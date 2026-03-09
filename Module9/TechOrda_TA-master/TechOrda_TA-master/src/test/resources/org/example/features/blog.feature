Feature: Blog Page Tests

  Scenario: BLO-03 Verify Filter Logic
    Given I am on the Blog page
    When I select "TOPICS: FinTech"
    Then the result set shows blogs related to FinTech