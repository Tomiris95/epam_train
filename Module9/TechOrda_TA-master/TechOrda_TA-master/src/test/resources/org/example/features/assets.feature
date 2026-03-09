Feature: Assets Page Tests

  Scenario: ASST-03 Verify asset detail page opens
    Given I am on the Assets catalog page
    When I click on any asset card
    Then the Asset detail page opens with detailed information about the asset

  Scenario: ASST-05 Verify system behavior when no assets are available
    Given user is on the Assets page
    When user applies filters:
        | COMPETENCY CENTERS | AI/ML Capabilities |
        | TYPES             | Method & Template    |
    Then a "Sorry, we couldn't find any matching results" message should be displayed