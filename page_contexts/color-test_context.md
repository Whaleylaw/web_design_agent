# Page Context: color-test

## Visual Layout Description

## Main Headings
- h1: Color Test Page

## Main Content
- Color Test PageThis page is used to test background colors.
- This page is used to test background colors.


## Element Mapping for Agent Reference

When a user refers to page elements, use this mapping to find the correct HTML:

**"color test page"** → `<h1 style="color: white;">Color Test Page</h1>`

**"color"** → `<h1 style="color: white;">Color Test Page</h1>`

**"test"** → `<h1 style="color: white;">Color Test Page</h1>`

**"page"** → `<h1 style="color: white;">Color Test Page</h1>`


## Common User Descriptions

- "upper left corner" → Look in header or first heading elements
- "top of page" → Look in header section
- "navigation" → Look in nav elements or header links
- "main heading" → Look for h1 elements
- "title" → Look for h1, title tag, or prominent heading
- "button" → Look for button elements or links with button classes

## Search Strategy for Agent

1. When user describes a location (e.g., "upper left"), check the header section first
2. When user mentions text content, search headings first, then links, then other text
3. Use the element mapping above to quickly locate commonly referenced elements
4. If searching for specific text, use case-insensitive search across all text content

