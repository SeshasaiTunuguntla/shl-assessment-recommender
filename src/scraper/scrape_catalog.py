"""
SHL Product Catalog Scraper

Scrapes the SHL Individual Test Solutions catalog and structures it for the recommender system.
"""

import json
import time
from typing import List, Dict, Any
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SHLCatalogScraper:
    """Scrapes SHL product catalog with focus on Individual Test Solutions."""
    
    BASE_URL = "https://www.shl.com/solutions/products/product-catalog/"
    
    def __init__(self, output_dir: str = "data/catalog"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assessments = []
        
    def setup_driver(self):
        """Setup headless Chrome driver for dynamic content."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=chrome_options)
    
    def scrape_catalog_page(self) -> List[Dict[str, Any]]:
        """
        Scrape the main catalog page to get all Individual Test Solutions.
        
        Returns:
            List of assessment dictionaries with metadata
        """
        print(f"Scraping catalog from {self.BASE_URL}")
        
        driver = self.setup_driver()
        assessments = []
        
        try:
            driver.get(self.BASE_URL)
            # Wait for dynamic content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-item"))
            )
            time.sleep(2)  # Additional wait for JS rendering
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all product cards/items
            product_items = soup.find_all(class_="product-item")
            
            for item in product_items:
                try:
                    assessment = self._parse_product_item(item)
                    if assessment and self._is_individual_test(assessment):
                        assessments.append(assessment)
                        print(f"Found: {assessment['name']}")
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
                    
        finally:
            driver.quit()
        
        self.assessments = assessments
        return assessments
    
    def _parse_product_item(self, item: BeautifulSoup) -> Dict[str, Any]:
        """Extract assessment details from a product item."""
        assessment = {}
        
        # Extract name
        title_elem = item.find(['h3', 'h4', 'h5'], class_=['product-title', 'title'])
        assessment['name'] = title_elem.text.strip() if title_elem else "Unknown"
        
        # Extract URL
        link_elem = item.find('a', href=True)
        assessment['url'] = link_elem['href'] if link_elem else ""
        if assessment['url'] and not assessment['url'].startswith('http'):
            assessment['url'] = f"https://www.shl.com{assessment['url']}"
        
        # Extract description
        desc_elem = item.find(['p', 'div'], class_=['description', 'product-desc'])
        assessment['description'] = desc_elem.text.strip() if desc_elem else ""
        
        # Extract test type (K=Knowledge, P=Personality, A=Ability, etc.)
        assessment['test_type'] = self._infer_test_type(assessment)
        
        # Extract metadata
        assessment['category'] = self._extract_category(item)
        assessment['duration'] = self._extract_duration(item)
        assessment['level'] = self._extract_level(item)
        
        return assessment
    
    def _is_individual_test(self, assessment: Dict[str, Any]) -> bool:
        """Filter out Job Solutions, only keep Individual Test Solutions."""
        name_lower = assessment['name'].lower()
        desc_lower = assessment.get('description', '').lower()
        
        # Exclude job solutions
        exclude_keywords = ['job solution', 'job profile', 'package', 'bundle']
        if any(keyword in name_lower or keyword in desc_lower for keyword in exclude_keywords):
            return False
        
        # Include individual tests
        include_keywords = ['test', 'assessment', 'questionnaire', 'inventory']
        return any(keyword in name_lower or keyword in desc_lower for keyword in include_keywords)
    
    def _infer_test_type(self, assessment: Dict[str, Any]) -> str:
        """Infer test type from name and description."""
        text = (assessment['name'] + ' ' + assessment.get('description', '')).lower()
        
        if any(kw in text for kw in ['personality', 'opq', 'motivation', 'behavioral']):
            return 'P'  # Personality
        elif any(kw in text for kw in ['coding', 'programming', 'java', 'python', 'technical']):
            return 'K'  # Knowledge/Technical
        elif any(kw in text for kw in ['numerical', 'verbal', 'inductive', 'deductive', 'cognitive']):
            return 'A'  # Ability
        elif any(kw in text for kw in ['situational', 'judgment', 'sjt']):
            return 'S'  # Situational
        else:
            return 'O'  # Other
    
    def _extract_category(self, item: BeautifulSoup) -> str:
        """Extract assessment category/domain."""
        category_elem = item.find(class_=['category', 'product-category'])
        return category_elem.text.strip() if category_elem else "General"
    
    def _extract_duration(self, item: BeautifulSoup) -> str:
        """Extract test duration if available."""
        duration_elem = item.find(class_=['duration', 'time'])
        return duration_elem.text.strip() if duration_elem else ""
    
    def _extract_level(self, item: BeautifulSoup) -> str:
        """Extract seniority level if available."""
        level_elem = item.find(class_=['level', 'seniority'])
        return level_elem.text.strip() if level_elem else ""
    
    def scrape_detailed_pages(self):
        """Optionally scrape individual assessment pages for more details."""
        driver = self.setup_driver()
        
        for assessment in self.assessments:
            if not assessment.get('url'):
                continue
                
            try:
                print(f"Scraping details for: {assessment['name']}")
                driver.get(assessment['url'])
                time.sleep(2)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Extract additional details
                details = self._parse_detail_page(soup)
                assessment.update(details)
                
            except Exception as e:
                print(f"Error scraping {assessment['url']}: {e}")
                continue
        
        driver.quit()
    
    def _parse_detail_page(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse individual assessment detail page."""
        details = {}
        
        # Extract full description
        desc_section = soup.find('div', class_=['description', 'overview'])
        if desc_section:
            details['full_description'] = desc_section.get_text(strip=True)
        
        # Extract key features
        features = soup.find_all('li', class_=['feature', 'benefit'])
        if features:
            details['features'] = [f.get_text(strip=True) for f in features]
        
        # Extract competencies measured
        competencies = soup.find('div', class_=['competencies', 'measures'])
        if competencies:
            details['competencies'] = competencies.get_text(strip=True)
        
        return details
    
    def save_catalog(self):
        """Save scraped catalog to JSON file."""
        output_file = self.output_dir / "shl_catalog.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.assessments, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved {len(self.assessments)} assessments to {output_file}")
        
        # Also save a summary
        summary = {
            'total_assessments': len(self.assessments),
            'test_types': self._count_by_type(),
            'categories': self._count_by_category()
        }
        
        summary_file = self.output_dir / "catalog_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Saved summary to {summary_file}")
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count assessments by test type."""
        counts = {}
        for assessment in self.assessments:
            test_type = assessment.get('test_type', 'O')
            counts[test_type] = counts.get(test_type, 0) + 1
        return counts
    
    def _count_by_category(self) -> Dict[str, int]:
        """Count assessments by category."""
        counts = {}
        for assessment in self.assessments:
            category = assessment.get('category', 'General')
            counts[category] = counts.get(category, 0) + 1
        return counts


def main():
    """Main scraping workflow."""
    scraper = SHLCatalogScraper()
    
    # Scrape catalog
    assessments = scraper.scrape_catalog_page()
    
    if not assessments:
        print("Warning: No assessments found. Check the scraper selectors.")
        return
    
    # Optionally scrape detailed pages (takes longer)
    # scraper.scrape_detailed_pages()
    
    # Save results
    scraper.save_catalog()
    
    print(f"\nTotal assessments scraped: {len(assessments)}")


if __name__ == "__main__":
    main()
