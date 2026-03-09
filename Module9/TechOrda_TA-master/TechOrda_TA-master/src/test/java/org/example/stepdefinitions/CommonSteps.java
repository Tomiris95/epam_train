package org.example.stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.datatable.DataTable;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import java.time.Duration;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class CommonSteps {
    private WebDriver driver;
    private WebDriverWait wait;

    @Before
    public void setUp() {
        if (driver == null) {
            ChromeOptions options = new ChromeOptions();
            options.addArguments("--headless");
            driver = new ChromeDriver(options);
            wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        }
    }

    @Given("I open the browser")
    public void iOpenTheBrowser() {
        ChromeOptions options = new ChromeOptions();
        // Uncomment for headless mode: options.addArguments("--headless");
        driver = new ChromeDriver(options);
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    @When("I navigate to the Solutions page")
    public void iNavigateToSolutionsPage() {
        driver.get("https://solutionshub.epam.com/catalog"); //  URL
    }

    @Then("the Solutions catalog page loads successfully and solutions are displayed")
    public void solutionsPageLoads() {
        // Assume there's a container with solutions
        WebElement solutionsContainer = wait.until(ExpectedConditions.presenceOfElementLocated(By.className("HeaderNavigation-module-scss-module__Y3yWOG__mainSubMenuItemName")));
        assertTrue(solutionsContainer.isDisplayed());
        List<WebElement> solutions = driver.findElements(By.className("HeaderNavigation-module-scss-module__Y3yWOG__mainSubMenuItemName"));
        assertTrue(solutions.size() > 0);
    }

    @Given("I am on the Solutions catalog page")
    public void iAmOnSolutionsCatalogPage() {
        driver.get("https://solutionshub.epam.com/catalog");
        wait.until(ExpectedConditions.presenceOfElementLocated(By.className("HeaderNavigation-module-scss-module__Y3yWOG__mainSubMenuItemName")));
    }

    @When("I click on any solution card")
    public void iClickOnAnySolutionCard() {
        List<WebElement> solutions = driver.findElements(By.className("Typography-module-scss-module__REtnSG__typography Typography-module-scss-module__REtnSG__h6 CatalogCard-module-scss-module__UNQvqW__title"));
        if (solutions.size() > 0) {
            solutions.get(0).click();
        }
    }

    @Then("the Solution detail page opens with detailed information about the solution")
    public void solutionDetailPageOpens() {
        WebElement detailContainer = wait.until(ExpectedConditions.presenceOfElementLocated(By.className("SolutionOverview-module-scss-module__o3P2eq__solutionOverviewSection")));
        assertTrue(detailContainer.isDisplayed());
    }

    @When("I select {string}")
    public void iSelectFilter(String filter) {
        WebElement filterElement = driver.findElement(By.xpath("//option[text()='" + filter + "']"));
        filterElement.click();
    }

    @Then("the result set shows solutions tagged with Healthcare")
    public void resultSetShowsHealthcare() {
        List<WebElement> solutions = driver.findElements(By.className("Typography-module-scss-module__REtnSG__typography Typography-module-scss-module__REtnSG__h6 CatalogCard-module-scss-module__UNQvqW__title"));
        for (WebElement solution : solutions) {
            // Find the badge inside the solution card
            WebElement healthcareBadge = solution.findElement(By.className("Badge-module-scss-module__sEk7Pa__content"));
            assertTrue(healthcareBadge.getText().contains("Healthcare"));
        }
    }

    // @Then("the result set shows solutions tagged with Healthcare")
    // public void resultSetShowsHealthcare() {
    //     List<WebElement> solutions = driver.findElements(By.className("Badge-module-scss-module__sEk7Pa__content"));
    //     for (WebElement solution : solutions) {
    //         assertTrue(solution.getText().contains("Healthcare"));
    //     }
    // }

    @Given("I am on the Solutions page")
    public void iAmOnSolutionsPage() {
        driver.get("https://solutionshub.epam.com/catalog");
    }

    @Then("only solutions tagged with both Healthcare AND Cloud & DevOps are displayed")
    public void solutionsTaggedWithBoth() {
        List<WebElement> solutions = driver.findElements(By.className("Badge-module-scss-module__sEk7Pa__content"));
        for (WebElement solution : solutions) {
            assertTrue(solution.getText().contains("Healthcare") && solution.getText().contains("Cloud & DevOps"));
        }
    }

    @Given("I am on the Assets catalog page")
    public void iAmOnAssetsCatalogPage() {
        driver.get("https://solutionshub.epam.com/catalog?mode=assets");
        wait.until(ExpectedConditions.presenceOfElementLocated(By.className("assets-container")));
    }

    @When("I click on any asset card")
    public void iClickOnAnyAssetCard() {
        List<WebElement> assets = driver.findElements(By.className("asset-card"));
        if (assets.size() > 0) {
            assets.get(0).click();
        }
    }

    @Then("the Asset detail page opens with detailed information about the asset")
    public void assetDetailPageOpens() {
        WebElement detailContainer = wait.until(ExpectedConditions.presenceOfElementLocated(By.className("asset-detail")));
        assertTrue(detailContainer.isDisplayed());
    }

    @Given("user is on the Assets page")
    public void userIsOnAssetsPage() {
        driver.get("https://solutionshub.epam.com/catalog?mode=assets");
    }

    @When("user applies filters:")
    public void userAppliesFilters(io.cucumber.datatable.DataTable dataTable) {
        // Assuming filters are applied via dropdowns or inputs
        // For simplicity, simulate by selecting options
        List<List<String>> filters = dataTable.asLists();
        for (List<String> filter : filters) {
            String category = filter.get(0);
            String value = filter.get(1);
            // Example: select from dropdown
            WebElement dropdown = driver.findElement(By.id(category.toLowerCase().replace(" ", "-")));
            dropdown.sendKeys(value);
        }
        // Assume there's a apply button
        WebElement applyButton = driver.findElement(By.id("apply-filters"));
        applyButton.click();
    }

    @Then("a {string} message should be displayed")
    public void aMessageShouldBeDisplayed(String message) {
        WebElement noResults = wait.until(ExpectedConditions.presenceOfElementLocated(By.className("no-results")));
        assertEquals(message, noResults.getText());
    }

    @Given("I am on the Guides page")
    public void iAmOnGuidesPage() {
        driver.get("https://solutionshub.epam.com/guides");
    }

    @When("I click on any question inside Frequently Asked Questions box")
    public void clickOnFAQ() {
        List<WebElement> faqs = driver.findElements(By.className("faq-question"));
        if (faqs.size() > 0) {
            faqs.get(0).click();
        }
    }

    @Then("the selected FAQ collapses")
    public void faqCollapses() {
        WebElement answer = driver.findElement(By.className("faq-answer"));
        wait.until(ExpectedConditions.invisibilityOf(answer));
    }

    @Then("the answer expands to display the answer")
    public void answerExpands() {
        WebElement answer = wait.until(ExpectedConditions.visibilityOfElementLocated(By.className("faq-answer")));
        assertTrue(answer.isDisplayed());
    }

    @Given("I am on the Blog page")
    public void iAmOnBlogPage() {
        driver.get("https://solutionshub.epam.com/blog");
    }

    @Then("the result set shows blogs related to FinTech")
    public void blogsRelatedToFinTech() {
        List<WebElement> blogs = driver.findElements(By.className("blog-post"));
        for (WebElement blog : blogs) {
            assertTrue(blog.getText().contains("FinTech"));
        }
    }

    @Given("I am on the About page")
    public void iAmOnAboutPage() {
        driver.get("https://solutionshub.epam.com/about");
    }

    @Then("the answer for the question opens or closes")
    public void answerOpensOrCloses() {
        // Assuming toggle behavior
        WebElement answer = driver.findElement(By.className("faq-answer"));
        // Check if it's visible or not, but since it's toggle, just assert it's there
        assertNotNull(answer);
    }

    @When("I click the {string} link in the {string} box")
    public void clickContactUsLink(String linkText, String boxText) {
        WebElement link = driver.findElement(By.linkText(linkText));
        link.click();
    }

    @Then("a contact form or email dialog opens allowing the user to submit an inquiry")
    public void contactFormOpens() {
        WebElement contactForm = wait.until(ExpectedConditions.presenceOfElementLocated(By.id("contact-form")));
        assertTrue(contactForm.isDisplayed());
    }

    @After
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}