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
  const TOOL_DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
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
      version: null,
      lastUpdated: null,
      revisionCount: null,
    };
  }

  async function loadCatalog(url = "./catalog.json") {
    const response = await fetch(url);
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

  async function loadToolMetadata(url = "./data/homepage-tool-meta.json") {
    const response = await fetch(url);
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

  function mergeToolMetadata(tools, metadata = {}) {
    return tools.map((tool) => {
      const entry = metadata[toolMetadataKey(tool.path)] || {};
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

  async function loadCatalogWithMetadata(
    catalogUrl = "./catalog.json",
    metadataUrl = "./data/homepage-tool-meta.json",
  ) {
    const catalogPromise = loadCatalog(catalogUrl);
    const metadataPromise = loadToolMetadata(metadataUrl).catch((error) => {
      console.warn(
        "Tool metadata is unavailable; loading the catalog without it.",
        error,
      );
      return {};
    });
    const [tools, metadata] = await Promise.all([
      catalogPromise,
      metadataPromise,
    ]);
    return mergeToolMetadata(tools, metadata);
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

  function toolHref(path) {
    return String(path || "#");
  }

  function toolMetadataKey(path) {
    const normalized = String(path || "")
      .replace(/^https?:\/\/[^/]+/i, "")
      .split(/[?#]/, 1)[0]
      .replace(/^\.\//, "/");
    if (!normalized) return "/";
    return normalized.endsWith("/") ? normalized : `${normalized}/`;
  }

  function formatToolDate(value) {
    if (!value) return "Date unavailable";
    const date = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(date.getTime())) return "Date unavailable";
    return TOOL_DATE_FORMATTER.format(date);
  }

  function visibleTags(tool, maximum = 4) {
    const limit = Number.isInteger(maximum) && maximum > 0 ? maximum : 4;
    return (tool.tags || [])
      .filter((tag) => !HUMAN_VERIFIED_TAGS.has(normalizedText(tag)))
      .slice(0, limit);
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
      element.append(
        child instanceof Node ? child : document.createTextNode(child),
      );
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

  window.HomepageIndex = Object.freeze({
    createElement,
    createStatusMark,
    filterTools,
    getFilters,
    groupTools,
    loadCatalog,
    loadCatalogWithMetadata,
    loadToolMetadata,
    mergeToolMetadata,
    populateCategorySelect,
    formatToolDate,
    toolHref,
    visibleTags,
  });
})();
