@domain:documentation-site @area:site-theme @from:docs/stylesheets
Feature: Branding the documentation site
  Gives readers of the docs and the GitHub Pages splash one consistent, privacy-respecting look in light and dark mode.

  Background:
    Given the documentation site and the splash page are published together

  @id:documentation-site.site-theme.001 @rule:docs.site-theme.one-accent-palette-shared-with-splash @inferred @source:docs/stylesheets/extra.css#:root @questionable
  Scenario: The docs and the splash page use the same orange-red accent pair
    Given the accent pair is orange #fb923c and red #ef4444
    When a reader opens the splash page and then the rendered docs
    Then the splash title and GitHub button use the orange-to-red gradient, and its install label and docs link use the red
    And the docs links and primary buttons use the same orange and red
    And changing the accent pair once changes both pages

  @id:documentation-site.site-theme.002 @rule:docs.site-theme.no-external-font-requests @inferred @source:docs/stylesheets/extra.css#:root
  Scenario: The docs load no web fonts and use the reader's system fonts
    Given a reader whose browser blocks all third-party requests
    When the reader opens any docs page
    Then body text shows in the system sans-serif stack starting with -apple-system
    And code shows in the system monospace stack starting with ui-monospace
    And no font is fetched from a font CDN

  @id:documentation-site.site-theme.003 @rule:docs.site-theme.legible-links-in-each-scheme @inferred @source:docs/stylesheets/extra.css#[data-md-color-scheme="slate"]
  Scenario Outline: Links use the accent colour that stays readable in the chosen colour scheme
    Given the reader has picked the <scheme> colour scheme
    When the reader views a docs page
    Then links are shown in <link_colour>
    And the page, header and tabs background is <background>

    Examples:
      | scheme | link_colour    | background                           |
      | light  | red #ef4444    | the theme's default light background |
      | dark   | orange #fb923c | near-black #0b0f1a                   |

  @id:documentation-site.site-theme.004 @rule:docs.site-theme.no-stand-in-logo @inferred @source:docs/stylesheets/extra.css#.md-header__button.md-logo
  Scenario: The docs header shows no logo while the project has none
    Given the site has no logo configured
    When a reader opens any docs page
    Then the header shows the site title without a logo icon
    And the navigation drawer title shows no logo icon
