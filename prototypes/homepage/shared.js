(function () {
  "use strict";

  const DISPLAY_GROUPS = Object.freeze([
    {
      id: "mechanical",
      label: "Mechanical & Structures",
      rawCategories: [
        "Mechanical Engineering",
        "Structural Engineering",
        "Machine Design",
        "Fasteners",
      ],
    },
    {
      id: "thermal",
      label: "Thermal & Fluids",
      rawCategories: ["Thermal Sciences", "Fluid Mechanics"],
    },
    {
      id: "electrical",
      label: "Electrical",
      rawCategories: ["Electrical Engineering", "Energy Storage"],
    },
    {
      id: "materials",
      label: "Materials & Manufacturing",
      rawCategories: ["Materials", "Manufacturing", "Chemical Engineering"],
    },
    {
      id: "reliability",
      label: "Reliability & Controls",
      rawCategories: [
        "Reliability",
        "Reliability Engineering",
        "Control Systems",
      ],
    },
    {
      id: "acoustics",
      label: "Acoustics & Vibration",
      rawCategories: ["Acoustics"],
    },
    {
      id: "reference",
      label: "Reference & Utilities",
      rawCategories: [
        "Reference",
        "Utility",
        "Education",
        "Business",
        "Strategy",
        "Games",
      ],
    },
    {
      id: "aerospace",
      label: "Aerospace",
      rawCategories: ["Aerospace", "Aerospace Engineering"],
    },
  ]);

  const GROUP_BY_ID = new Map(DISPLAY_GROUPS.map((group) => [group.id, group]));
  const RAW_CATEGORY_TO_GROUP = new Map();
  DISPLAY_GROUPS.forEach((group) => {
    group.rawCategories.forEach((category) => {
      RAW_CATEGORY_TO_GROUP.set(category, group.id);
    });
  });

  // Specific disciplines win over broad categories when a tool has several labels.
  const PRIMARY_GROUP_PRIORITY = Object.freeze([
    "aerospace",
    "acoustics",
    "reliability",
    "electrical",
    "thermal",
    "materials",
    "mechanical",
    "reference",
  ]);

  const HUMAN_VERIFIED_TAGS = new Set([
    "human-verified",
    "human verified",
    "human_checked",
    "human checked",
    "human-reviewed",
    "human reviewed",
  ]);

  const PRIORITY_TOOL_TITLES = Object.freeze([
    "Unit Converter",
    "Reynolds Number Explorer",
    "Battery Runtime Estimator",
    "Bolt Torque Calculator (VDI 2230)",
    "Beam Bending Calculator",
    "Engineering Fits Assistant",
  ]);

  const VERIFIED_LABEL = "Verified";
  const EXPERIMENTAL_LABEL = "Experimental";

  const PREVIEW_ART = Object.freeze({
    mechanical: `
      <path d="M360 96v138M540 96v138M344 234h212"/>
      <path d="M380 166c44 50 96 50 140 0"/>
      <path d="M405 102v54m0 0-10-16m10 16 10-16M450 102v72m0 0-10-16m10 16 10-16M495 102v54m0 0-10-16m10 16 10-16"/>
    `,
    thermal: `
      <rect x="360" y="108" width="176" height="112" rx="8"/>
      <path d="M382 136h132M382 164h132M382 192h132"/>
      <path d="M392 82v18m0-18-9 12m9-12 9 12M448 82v18m0-18-9 12m9-12 9 12M504 82v18m0-18-9 12m9-12 9 12"/>
    `,
    electrical: `
      <path d="M354 166h42l17-34 32 68 26-52 18 36h56"/>
      <circle cx="354" cy="166" r="8"/><circle cx="545" cy="166" r="8"/>
      <path d="M374 104h150M374 228h150M389 96v16M509 96v16M389 220v16M509 220v16"/>
    `,
    materials: `
      <path d="m378 118 48-28 48 28v56l-48 28-48-28zM426 90v56m-48-28 48 28 48-28M426 146v56"/>
      <path d="m474 118 48-28 48 28v56l-48 28-48-28M474 174l48-28 48 28M522 90v56m0 0v56"/>
    `,
    reliability: `
      <rect x="350" y="136" width="62" height="54" rx="6"/>
      <rect x="438" y="136" width="62" height="54" rx="6"/>
      <rect x="526" y="136" width="62" height="54" rx="6"/>
      <path d="M330 163h20m62 0h26m62 0h26m62 0h20"/>
      <path d="m370 163 12 12 22-30M458 163l12 12 22-30M546 163l12 12 22-30"/>
    `,
    acoustics: `
      <path d="M338 164c22-72 44 72 66 0s44-72 66 0 44 72 66 0 44-72 66 0"/>
      <path d="M338 220h264M360 210v20M414 210v20M468 210v20M522 210v20M576 210v20"/>
    `,
    reference: `
      <rect x="350" y="94" width="220" height="142" rx="7"/>
      <path d="M374 120h172M374 148h172M374 176h172M374 204h172M414 108v112M458 108v112M502 108v112"/>
      <path d="M350 250h220M350 242v16M394 242v10M438 242v16M482 242v10M526 242v16M570 242v10"/>
    `,
    aerospace: `
      <path d="M340 172c62-44 144-62 246-28-78 7-142 30-198 68l-48-40z"/>
      <path d="M430 151l42-68 28 3-18 63M448 186l58 62 30-3-40-80"/>
    `,
  });

  function normalizedText(value) {
    return String(value || "").trim().toLowerCase();
  }

  function isVerified(tool) {
    return (tool.tags || []).some((tag) =>
      HUMAN_VERIFIED_TAGS.has(normalizedText(tag)),
    );
  }

  function isTemplate(tool) {
    return (tool.category || []).some(
      (category) => normalizedText(category) === "templates",
    );
  }

  function normalizeTool(tool, catalogIndex) {
    const rawCategories = Array.isArray(tool.category) ? tool.category : [];
    const tags = Array.isArray(tool.tags) ? tool.tags : [];
    const mappedGroupIds = new Set(
      rawCategories
        .map((category) => RAW_CATEGORY_TO_GROUP.get(category))
        .filter(Boolean),
    );

    if (!mappedGroupIds.size) {
      mappedGroupIds.add("reference");
    }

    const primaryGroupId =
      PRIMARY_GROUP_PRIORITY.find((groupId) => mappedGroupIds.has(groupId)) ||
      "reference";
    const verified = isVerified({ tags });
    const priorityRank = PRIORITY_TOOL_TITLES.indexOf(tool.title);

    return {
      title: String(tool.title || "Untitled tool"),
      path: String(tool.path || "#"),
      description: String(tool.description || ""),
      category: rawCategories,
      tags,
      catalogIndex,
      displayGroupIds: Array.from(mappedGroupIds),
      primaryGroupId,
      verified,
      statusLabel: verified ? VERIFIED_LABEL : EXPERIMENTAL_LABEL,
      priorityRank,
      upNext: !verified && priorityRank !== -1,
    };
  }

  async function loadCatalog(url = "/catalog.json") {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Catalog request failed with status ${response.status}.`);
    }

    const data = await response.json();
    if (!Array.isArray(data)) {
      throw new TypeError("Catalog response must be an array.");
    }

    return data
      .filter((tool) => !isTemplate(tool))
      .map((tool, catalogIndex) => normalizeTool(tool, catalogIndex));
  }

  async function loadToolMetadata(
    url = "/prototypes/homepage/tool-meta.json",
  ) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(
        `Tool metadata request failed with status ${response.status}.`,
      );
    }

    const data = await response.json();
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new TypeError("Tool metadata response must be an object.");
    }
    return data;
  }

  async function loadCatalogWithMetadata(
    catalogUrl = "/catalog.json",
    metadataUrl = "/prototypes/homepage/tool-meta.json",
  ) {
    const [tools, metadata] = await Promise.all([
      loadCatalog(catalogUrl),
      loadToolMetadata(metadataUrl),
    ]);

    return tools.map((tool) => {
      const entry = metadata[toolUrl(tool.path)] || {};
      const revisionCount = Number(entry.revision_count);
      return {
        ...tool,
        version:
          typeof entry.version === "string" && entry.version.trim()
            ? entry.version.trim()
            : null,
        lastUpdated:
          typeof entry.last_updated === "string" ? entry.last_updated : null,
        revisionCount:
          Number.isInteger(revisionCount) && revisionCount > 0
            ? revisionCount
            : null,
      };
    });
  }

  function getFilters(controls) {
    return {
      query: controls.searchInput
        ? normalizedText(controls.searchInput.value)
        : "",
      category: controls.categorySelect
        ? controls.categorySelect.value
        : "all",
      status: controls.statusSelect ? controls.statusSelect.value : "all",
    };
  }

  function searchableText(tool) {
    const displayLabels = tool.displayGroupIds.map(
      (groupId) => GROUP_BY_ID.get(groupId)?.label || "",
    );
    return normalizedText(
      [
        tool.title,
        tool.description,
        ...tool.tags,
        ...tool.category,
        ...displayLabels,
      ].join(" "),
    );
  }

  function filterTools(tools, filters) {
    return tools.filter((tool) => {
      const matchesQuery =
        !filters.query || searchableText(tool).includes(filters.query);
      const matchesCategory =
        filters.category === "all" ||
        tool.displayGroupIds.includes(filters.category);
      const matchesStatus =
        filters.status === "all" ||
        (filters.status === "verified" && tool.verified) ||
        (filters.status === "experimental" && !tool.verified);
      return matchesQuery && matchesCategory && matchesStatus;
    });
  }

  function compareTools(a, b) {
    if (a.verified !== b.verified) return a.verified ? -1 : 1;
    if (a.upNext !== b.upNext) return a.upNext ? -1 : 1;
    if (a.upNext && b.upNext) return a.priorityRank - b.priorityRank;
    return a.title.localeCompare(b.title);
  }

  function sortTools(tools) {
    return [...tools].sort(compareTools);
  }

  function groupTools(tools, selectedGroupId = "all") {
    if (selectedGroupId !== "all" && GROUP_BY_ID.has(selectedGroupId)) {
      return [
        {
          ...GROUP_BY_ID.get(selectedGroupId),
          tools: sortTools(
            tools.filter((tool) =>
              tool.displayGroupIds.includes(selectedGroupId),
            ),
          ),
        },
      ];
    }

    return DISPLAY_GROUPS.map((group) => ({
      ...group,
      tools: sortTools(
        tools.filter((tool) => tool.primaryGroupId === group.id),
      ),
    })).filter((group) => group.tools.length);
  }

  function countForGroup(tools, groupId) {
    return tools.filter((tool) => tool.displayGroupIds.includes(groupId)).length;
  }

  function populateCategorySelect(select, tools) {
    if (!select) return;
    select.replaceChildren();

    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = `All disciplines (${tools.length})`;
    select.appendChild(allOption);

    DISPLAY_GROUPS.forEach((group) => {
      const count = countForGroup(tools, group.id);
      if (!count) return;
      const option = document.createElement("option");
      option.value = group.id;
      option.textContent = `${group.label} (${count})`;
      select.appendChild(option);
    });
  }

  function stats(tools) {
    const verified = tools.filter((tool) => tool.verified).length;
    return {
      total: tools.length,
      verified,
      experimental: tools.length - verified,
      groups: DISPLAY_GROUPS.filter(
        (group) => countForGroup(tools, group.id) > 0,
      ).length,
    };
  }

  function shouldRevealExperimental(filters) {
    return Boolean(filters.query) || filters.status === "experimental";
  }

  function toolUrl(path) {
    if (/^(?:https?:|\/|#)/.test(path)) return path;
    return `/${path.replace(/^\.\//, "")}`;
  }

  function formatToolDate(value) {
    if (!value) return "Date unavailable";
    const date = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(date.getTime())) return "Date unavailable";
    return new Intl.DateTimeFormat("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(date);
  }

  function visibleTags(tool, maximum = 4) {
    const limit = Number.isInteger(maximum) && maximum > 0 ? maximum : 4;
    return (tool.tags || [])
      .filter((tag) => !HUMAN_VERIFIED_TAGS.has(normalizedText(tag)))
      .slice(0, limit);
  }

  function escapeXml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&apos;");
  }

  function previewTitleLines(title, maximumLength = 27) {
    const words = String(title || "Engineering tool").split(/\s+/);
    const lines = [""];
    words.forEach((word) => {
      const current = lines.at(-1);
      if (!current || `${current} ${word}`.length <= maximumLength) {
        lines[lines.length - 1] = current ? `${current} ${word}` : word;
      } else if (lines.length < 2) {
        lines.push(word);
      }
    });
    if (words.join(" ").length > lines.join(" ").length) {
      lines[lines.length - 1] = `${lines.at(-1).replace(/[.,;:]$/, "")}...`;
    }
    return lines;
  }

  function previewDataUrl(tool) {
    const group = GROUP_BY_ID.get(tool.primaryGroupId) || GROUP_BY_ID.get("reference");
    const titleLines = previewTitleLines(tool.title);
    const titleMarkup = titleLines
      .map(
        (line, index) =>
          `<tspan x="42" dy="${index === 0 ? 0 : 34}">${escapeXml(line)}</tspan>`,
      )
      .join("");
    const artwork = PREVIEW_ART[tool.primaryGroupId] || PREVIEW_ART.reference;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
      <rect width="640" height="360" fill="#f8f9fb"/>
      <path d="M0 48h640M0 312h640" stroke="#e5e7eb" stroke-width="1"/>
      <text x="42" y="82" fill="#6b7280" font-family="SFMono-Regular,Menlo,monospace" font-size="13" letter-spacing="1.4">${escapeXml(group.label.toUpperCase())}</text>
      <text x="42" y="136" fill="#111827" font-family="Helvetica Neue,Arial,sans-serif" font-size="27" font-weight="600">${titleMarkup}</text>
      <g fill="none" stroke="#111827" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">${artwork}</g>
      <rect x="42" y="284" width="62" height="4" fill="#0f766e"/>
      <text x="118" y="291" fill="#4b5563" font-family="SFMono-Regular,Menlo,monospace" font-size="12">TRANSPARENT.TOOLS</text>
    </svg>`;
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
  }

  function createElement(tagName, options = {}, children = []) {
    const element = document.createElement(tagName);
    Object.entries(options).forEach(([key, value]) => {
      if (key === "className") {
        element.className = value;
      } else if (key === "text") {
        element.textContent = value;
      } else if (key === "dataset") {
        Object.assign(element.dataset, value);
      } else if (key === "attributes") {
        Object.entries(value).forEach(([name, attributeValue]) => {
          element.setAttribute(name, attributeValue);
        });
      } else if (key in element) {
        element[key] = value;
      } else {
        element.setAttribute(key, value);
      }
    });

    const childList = Array.isArray(children) ? children : [children];
    childList.filter(Boolean).forEach((child) => {
      element.append(child instanceof Node ? child : document.createTextNode(child));
    });
    return element;
  }

  function createStatusMark(tool, className = "status-mark") {
    return createElement("span", {
      className: `${className} ${tool.verified ? "is-verified" : "is-experimental"}`,
      attributes: {
        "aria-label": tool.statusLabel,
        title: tool.verified
          ? "Reviewed and verified by a human maintainer."
          : "Experimental and not yet fully verified.",
      },
    });
  }

  function setCurrentYear(target) {
    if (target) target.textContent = new Date().getFullYear();
  }

  window.HomepagePrototype = Object.freeze({
    DISPLAY_GROUPS,
    GROUP_BY_ID,
    PRIORITY_TOOL_TITLES,
    VERIFIED_LABEL,
    EXPERIMENTAL_LABEL,
    compareTools,
    countForGroup,
    createElement,
    createStatusMark,
    filterTools,
    getFilters,
    groupTools,
    loadCatalog,
    loadCatalogWithMetadata,
    loadToolMetadata,
    populateCategorySelect,
    previewDataUrl,
    formatToolDate,
    setCurrentYear,
    shouldRevealExperimental,
    sortTools,
    stats,
    toolUrl,
    visibleTags,
  });
})();
