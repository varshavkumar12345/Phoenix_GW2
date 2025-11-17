import scrapy
from scrapy.crawler import CrawlerProcess
import os
import json


class GoogleNewsSpider(scrapy.Spider):
    name = "google_news"
    start_urls = ["https://news.google.com/rss"]

    def parse(self, response):
        for item in response.xpath("//item"):
            yield {
                "title": item.xpath("title/text()").get(),
                "link": item.xpath("link/text()").get(),
                "pubDate": item.xpath("pubDate/text()").get(),
                "source": item.xpath("source/text()").get(),
            }


class PrependJSONPipeline:

    filename = "googlenews.json"

    def open_spider(self, spider):
        # Load existing JSON data
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    self.old_data = json.load(f)
            except json.JSONDecodeError:
                self.old_data = []
        else:
            self.old_data = []

        self.new_data = []

    def process_item(self, item, spider):
        # Collect freshly scraped items
        self.new_data.append(dict(item))
        return item

    def close_spider(self, spider):
        # Prepend new data
        updated = self.new_data + self.old_data

        # Write back to file
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=4, ensure_ascii=False)

        print(f"✔ Prepending complete: {len(self.new_data)} new items added.")


if __name__ == "__main__":

    process = CrawlerProcess(settings={
        "ITEM_PIPELINES": {"__main__.PrependJSONPipeline": 300},
        "LOG_LEVEL": "ERROR",
    })

    process.crawl(GoogleNewsSpider)
    process.start()
    print("✔ Crawling complete.")