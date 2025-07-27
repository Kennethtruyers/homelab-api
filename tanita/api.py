import asyncio
from playwright.async_api import async_playwright
from fastapi import APIRouter, Request
import json
from datetime import datetime
from influxdb import InfluxDBClient
from datetime import datetime
from dotenv import load_dotenv
from connections import get_influx_client
import os

TANITA_EMAIL = os.getenv("TANITA_EMAIL")
TANITA_PASSWORD = os.getenv("TANITA_PASSWORD")

router = APIRouter()
load_dotenv()

@router.post("/scrape")
async def scrape(playwright):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        # Go to login page
        print("Loading login page")
        await page.goto("https://mytanita.eu/en/user/login")

        # Fill login form
        await page.wait_for_selector("input[name='mail']")
        await page.fill("input[name='mail']", TANITA_EMAIL)
        await page.fill("input[type='password']", TANITA_PASSWORD)
        await page.click("input[type='submit']")

        # Wait for dashboard to load (adjust if necessary)
        await page.wait_for_selector("text=My measurements", timeout=10000)

        # Navigate to history (if not redirected)
        await page.goto("https://mytanita.eu/en/user/measurements")

        # Wait for the data table/chart to render
        await page.wait_for_selector("table")  # adjust this selector based on actual DOM

        # Extract recent measurement from table
        data = []

        rows = await page.query_selector_all("table tbody tr")

        for row in rows:
            try:
                await row.click()
                await page.wait_for_timeout(100)  # brief wait for detail panel to update

                date_text = await page.inner_text("#date-value")
                weight = await page.inner_text("#weight-value")  # e.g. "70.60 KG"
                body_fat = await page.inner_text("#body_fat-value")  # e.g. "11.70 %"
                muscle_mass = await page.inner_text("#muscle_mass-value")
                visceral_fat = await page.inner_text("#visceral_fat-value")
                body_water = await page.inner_text("#body_water-value")
                bmr = await page.inner_text("#bmr-value")
                physique_rating = await page.inner_text("#physique_rating-value")
                metabolic_age = await page.inner_text("#metabolic_age-value")

                entry = {
                    "timestamp": datetime.strptime(date_text.strip(), "%d/%m/%Y").isoformat(),
                    "weight": float(weight.split()[0].replace(",", ".")),
                    "body_fat_pct": float(body_fat.split()[0].replace(",", ".")),
                    "muscle_mass": float(muscle_mass.split()[0].replace(",", ".")),
                    "visceral_fat": float(visceral_fat.split()[0].replace(",", ".")),
                    "body_water": float(body_water.split()[0].replace(",", ".")),
                    "bmr": float(bmr.split()[0].replace(",", ".")),
                    "physique_rating": float(physique_rating.split()[0].replace(",", ".")),
                    "metabolic_age": float(metabolic_age.split()[0].replace(",", ".")),
                }
                
                jsonEntry = {
                        "measurement": "tanita",
                        "tags": {
                            "source": "mytanita"
                        },
                        "time": entry["timestamp"],  # Already ISO8601
                        "fields": {k: v for k, v in entry.items() if k != "timestamp"}
                    }
                

                data.append(jsonEntry)

            except Exception as e:
                print(f"Error parsing detail view: {e}")

        await browser.close()

        # Print latest entry
        client = get_influx_client("fitness")
        client.write_points(data)
        print("Loaded data into Influx")

@router.post("/ingest-csv")
async def download_and_ingest_csv():
    download_csv()
    ingest_csv()

def safe_float(value):
    value = value.strip().replace(",", ".")
    return float(value) if value not in ("-", "", "–") else None
    
async def download_csv():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True,ignore_https_errors=True)
        page = await context.new_page()

        # Go to login page
        print("Loading login page")
        await page.goto("https://mytanita.eu/en/user/login")

        # Fill login form
        await page.wait_for_selector("input[name='mail']")
        await page.fill("input[name='mail']", TANITA_EMAIL)
        await page.fill("input[type='password']", TANITA_PASSWORD)
        await page.click("input[type='submit']")

        # Wait for dashboard to load (adjust if necessary)
        await page.wait_for_selector("text=My measurements", timeout=10000)

        # Trigger download
        print("triggering download")
        async with page.expect_download() as download_info:
            await page.evaluate("window.location.href = '/en/user/export-csv'")
        download = await download_info.value

        download_path = os.path.abspath("data.csv")
        await download.save_as(download_path)
        print(f"✅ Downloaded: {download_path}")
        await browser.close()

        return download_path

def ingest_csv():
    # --- Parse CSV ---
    entries = []
    with open("data.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                timestamp = datetime.strptime(row["Date"], "%Y-%m-%d %H:%M:%S").isoformat() + "Z"
                entry = {
                    "timestamp": timestamp,
                    "weight": safe_float(row["Weight (kg)"]),
                    "body_fat_pct": safe_float(row["Body Fat (%)"]),
                    "muscle_mass": safe_float(row["Muscle Mass (kg)"]),
                    "visceral_fat": safe_float(row["Visc Fat"]),
                    "body_water": safe_float(row["Body Water (%)"]),
                    "bmr": safe_float(row["BMR (kcal)"]),
                    "metabolic_age": safe_float(row["Metab Age"]),
                    "physique_rating": safe_float(row["Physique Rating"]),
                    "heart_rate": safe_float(row["Heart rate"]),
                }
                # Optionally include segmental muscle mass
                # entry["muscle_trunk"] = safe_float(row["Muscle mass - trunk"])

                # Drop None values to avoid Influx field errors
                fields = {k: v for k, v in entry.items() if k != "timestamp" and v is not None}

                if fields:  # Only write if we have at least one field
                    entries.append({
                        "measurement": "tanita",
                        "tags": {"source": "csv_export"},
                        "time": entry["timestamp"],
                        "fields": fields
                    })
            except Exception as e:
                print(f"Skipping row: {row['Date']} → {e}")

    # --- Write to InfluxDB ---
    client = get_influx_client("fitness")
    client.write_points(entries)

