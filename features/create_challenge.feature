@smoke @critical
Feature: User Login
  As a Challenge Configurer
  I want to log into my account
  So that I can configure a challenge

#  Background:
#    Given I navigate to the login page

  @smoke
  Scenario: Successful login with valid credentials
    When I log in as "challenge_configurer"
    And I click on "Challenges"
    When I click the "+ Create a challenge" button
    And I select "Online V1 (EDSH)" from dropdown
#    And I verify "General Info" section is enabled
    Then I verify text "Create a challenge"
    When I select "HPB Healthy Food & Dining" from "Division Name" dropdown
#    And I enter "Test Auto Challenge" in the "Challenge Name" field
    And I enter "Test Auto Challenge" in the Challenge Name field
    And I enter "Test Challenge Tagline" in the "Challenge Tagline" field
    And I enter "Test Challenge Details" in the "About this Challenge" field
    And I enter "https://www.google.com/" in the "Official Website" field
    And I enter "Test Challenge Key Details" in the "Key Details" field
    And I select "Self-Enrolled" radio button
    And I verify "Master Terms & Conditions" option is selected
    And I enter "testChallenge@mail.com" in the "Email" field
    And I click the "Next" button
#    And I verify "Participating Details" section is enabled
    And I select "Seasonal" radio button
    And I generate datetime "tomorrow at 10:30 am" and store it as "ChallengeStartTime"
    And I generate datetime "5 days from now at 2:00 pm" and store it as "ChallengeEndTime"
    And I select date range "${ChallengeStartTime}" to "${ChallengeEndTime}" in "Challenge Period" field
    And I generate datetime "tomorrow at 10:00 am" and store it as "RegistrationStartTime"
    And I generate datetime "5 days from now at 1:00 pm" and store it as "RegistrationEndTime"
    And I select date range "${RegistrationStartTime}" to "${RegistrationEndTime}" in "Registration Period" field
    And I enter "No Eligibility" in the "Eligibility Description" field
    And I click the "Next" button
    Then I verify text "Metrics"
    And I select "Food purchase" checkbox
#    And I select "Drink purchase" checkbox
    And I click the "Next" button
    Then I verify text "Healthpoints Award Category"
#    When I select "Issue Healthpoints for this challenge" checkbox
#    And I select "Lifestyle" from "Category" dropdown
    And I enter "$1" in the "Amount (SGD)" field
    And I click the "Next" button
    And I select "Daily Quota" radio button
#    And I enter "2" in the "Quota Limit" field
    And I enter "2" in the "Daily Quota" field [force ai]
    And I enter "1" in the "Position" field
    And I enter "10" in the "Healthpoints" field
    And I click the "Create Challenge" button


#    And I verify "Metrics" section is disabled
#    And I verify "Rewards" section is disabled
#    And I verify "Gamification" section is disabled
