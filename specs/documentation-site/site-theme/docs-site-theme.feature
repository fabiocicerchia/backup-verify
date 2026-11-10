@domain:documentation-site @area:site-theme @from:docs/stylesheets
Feature: Branding the documentation site
  Gives readers of the docs and the GitHub Pages splash one consistent, privacy-respecting look in light and dark mode.

  Background:
    Given the documentation site and the splash page are published together

  @id:documentation-site.site-theme.002 @rule:docs.site-theme.no-external-font-requests @inferred @source:docs/stylesheets/extra.css#:root
  Scenario: The docs load no web fonts and use the reader's system fonts
    Given a reader whose browser blocks all third-party requests
    When the reader opens any docs page
    Then body text shows in the system sans-serif stack starting with -apple-system
    And code shows in the system monospace stack starting with ui-monospace
    And no font is fetched from a font CDN
