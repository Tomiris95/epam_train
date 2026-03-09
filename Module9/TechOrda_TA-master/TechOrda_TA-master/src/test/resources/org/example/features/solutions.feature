Feature: Solutions Page Tests

  Scenario: SOL-01 Verify Solutions page loads successfully
    Given I open the browser
    When I navigate to the Solutions page
    Then the Solutions catalog page loads successfully and solutions are displayed

  Scenario: SOL-02 Verify solutions detail page opens
    Given I am on the Solutions catalog page
    When I click on any solution card
    Then the Solution detail page opens with detailed information about the solution

  Scenario: SOL-03 Verify Filter Logic
    Given I am on the Solutions catalog page
    When I select "INDUSTRIES: Healthcare"
    Then the result set shows solutions tagged with Healthcare

  Scenario: SOL-04 Multi-Filter Logic
    Given I am on the Solutions page
    When I select "INDUSTRIES: Healthcare"
    And I select "CATEGORIES: Cloud & DevOps"
    Then only solutions tagged with both Healthcare AND Cloud & DevOps are displayed