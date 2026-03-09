Feature: Guides Page Tests

  Scenario: GUI-03 Verify Frequently Asked Questions open
    Given I am on the Guides page
    When I click on any question inside Frequently Asked Questions box
    Then the selected FAQ collapses
    When I click on the same question again
    Then the answer expands to display the answer