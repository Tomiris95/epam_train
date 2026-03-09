Feature: About Page Tests

  Scenario: ABT-02 Verify Frequently Asked Questions open
    Given I am on the About page
    When I click on any question inside Frequently Asked Questions box
    Then the selected FAQ collapses
    When I click on the same question again
    Then the answer expands to display the answer

  Scenario: ABT-03 Verify contact Info
    Given I am on the About page
    When I click the "Contact us" link in the "Still have a question? We’d love to hear from you!" box
    Then a contact form or email dialog opens allowing the user to submit an inquiry