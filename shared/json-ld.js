/**
 * JSON-LD Structured Data Module
 *
 * Dynamically injects schema.org JSON-LD structured data into tool pages
 * on transparent.tools. Generates WebApplication and BreadcrumbList schemas
 * from existing page metadata.
 *
 * Usage:
 *   Include in any tool page's <head>:
 *   <script src="/shared/json-ld.js"></script>
 *
 * The script reads document.title, meta[name="description"], and the page URL
 * to populate the structured data. It only runs on pages whose URL contains
 * "/tools/".
 */
(function () {
    'use strict';

    /**
     * Return the text content of a <meta name="..."> tag, or null if missing.
     */
    function getMetaContent(name) {
        var el = document.querySelector('meta[name="' + name + '"]');
        return el ? el.getAttribute('content') : null;
    }

    /**
     * Inject a JSON-LD script element into <head>.
     */
    function injectJsonLd(data) {
        var script = document.createElement('script');
        script.type = 'application/ld+json';
        script.textContent = JSON.stringify(data, null, 2);
        document.head.appendChild(script);
    }

    /**
     * Build and inject all JSON-LD blocks for the current page.
     */
    function init() {
        var url = window.location.href;

        // Only run on tool pages
        if (url.indexOf('/tools/') === -1) {
            return;
        }

        var title = document.title || '';
        var description = getMetaContent('description') || '';

        // --- WebApplication schema ---
        var webApp = {
            '@context': 'https://schema.org',
            '@type': 'WebApplication',
            'name': title,
            'description': description,
            'url': url,
            'applicationCategory': 'Engineering',
            'operatingSystem': 'Any',
            'offers': {
                '@type': 'Offer',
                'price': '0',
                'priceCurrency': 'USD'
            },
            'author': {
                '@type': 'Organization',
                'name': 'Transparent Tools',
                'url': 'https://transparent.tools'
            },
            'browserRequirements': 'Requires JavaScript',
            'softwareVersion': '1.0',
            'isAccessibleForFree': true
        };

        injectJsonLd(webApp);

        // --- BreadcrumbList schema ---
        var breadcrumb = {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {
                    '@type': 'ListItem',
                    'position': 1,
                    'name': 'Home',
                    'item': 'https://transparent.tools/'
                },
                {
                    '@type': 'ListItem',
                    'position': 2,
                    'name': title,
                    'item': url
                }
            ]
        };

        injectJsonLd(breadcrumb);
    }

    // Run once the DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already loaded (e.g. script loaded with defer or at end of body)
        init();
    }
})();
