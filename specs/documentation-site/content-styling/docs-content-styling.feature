@domain:documentation-site @area:content-styling @from:docs/stylesheets
Feature: Styling documentation content
  Makes the docs home page and its calls to action read as the product's brand for prospective users.

  @id:documentation-site.content-styling.001 @rule:docs.content-styling.accent-gradient-calls-to-action @inferred @source:docs/stylesheets/extra.css#.md-typeset .hero h1 @questionable
  Scenario: The home page title and primary buttons are drawn in the accent gradient
    Given the docs home page has a hero with a title, a tagline and buttons
    When a reader opens the docs home page
    Then the hero title is centred and filled with the orange-to-red accent gradient
    And primary buttons are pill-shaped with the orange-to-red gradient and white text
    And hovering a button lifts it slightly with an indigo glow
