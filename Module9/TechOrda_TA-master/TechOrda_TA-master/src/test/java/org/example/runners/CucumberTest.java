package org.example.runners;

import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "classpath:org/example/features",
    glue = "org.example.stepdefinitions",
    plugin = {"pretty", "html:target/cucumber-reports/cucumber.html"}
)
public class CucumberTest {
}
