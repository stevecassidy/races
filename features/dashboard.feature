Feature: Club dashboard

    Scenario: dashboard link in navigation bar
    Given Alejandro is a club official for the MOV club
    And he is logged in to the site
    When he views any page on the site
    Then a link to the MOV club dashboard page is shown in the navigation bar


    Scenario: club statistics shown on dashboard page
    Given I am a club official
    When I view the club dashboard page
    Then I see a table of club statistics that include number of members in various categories
    And the page lists the members with roles within the club


    Scenario: rider search shown on the dashboard page
    Given I am a club official
    When I view the club dashboard page
    Then I see a search box that allows me to search for riders by name

    Scenario: rider search finds riders by name
    Given I am a club official
    And I am viewing the club dashboard page
    When I enter the text 'V' in the rider search box
    And I click the Search Riders button
    Then I see a page that contains links to all riders from all clubs with names containing 'V'
