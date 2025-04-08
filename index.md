---
layout: default
title: Tools
---

# Tools

Welcome to my collection of engineering calculators and mini-apps.

<ul>
{% for page in site.pages %}
  {% if page.url contains '/tools/' and page.url endswith '/index.html' and page.url != '/tools/index.html' %}
    <li>
      <a href="{{ page.url }}">
        {% if page.title %}
          {{ page.title }}
        {% else %}
          {{ page.url | remove:'/tools/' | remove:'/index.html' | capitalize }}
        {% endif %}
      </a>
    </li>
  {% endif %}
{% endfor %}
</ul>
