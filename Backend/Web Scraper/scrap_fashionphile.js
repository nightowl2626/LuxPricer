import * as cheerio from 'cheerio';

export async function get_fashionphile_links(url) {
    let fashionphile_links = [];

    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        };

        let site = await response.text();
        const $ = cheerio.load(site);

        $('div.hitsContainer ol a.hitTitle').each((id, element) => {
            fashionphile_links.push($(element).attr('href'));
        });

        return fashionphile_links;

    } catch (error) {
        console.error('Error fetching or parsing the URL:', error);
        throw error; // Re-throw the error to handle it in the async call
    }
};

export async function scrap_fashionphile(url) {
    let result = {};

    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        let site = await response.text();
        const $ = cheerio.load(site);

        result.listing_id = ""; // url_parser
        result.listing_url = url;
        result.listing_name = $('h1 span').text() || "";
        result.source_platform = "Fashionphile"; // url_parser
        result.listing_price = $('span.currPrice').text().replace("\$", "") || "";
        result.currency = "USD";
        result.location = $('locationModalTrigger').text() || ""; // Fix this selector if needed
        result.condition_rating = $('button.additionalText').text() || "";
        result.condition_description = [];
        $('div.accordionPanel.zero p').each((id, element) => {
            result.condition_description.push($(element).text() || "");
        });
        result.item_details = {
            category: $('div.accordionPanel.two p').text() || "",
            designer: $('h1 a').text() || "",
            model: $('h1 span').text() || "", // Fix this selector if needed
            item_description: $('meta[name="description"]').attr('content') || "",
            size: [],
            material: "", // LLMs extraction
            color: "" // LLMs extraction
        };
        $('div.accordionPanel.four p').each((id, element) => {
            result.item_details.size.push($(element).text() || "");
        });
        result.inclusions = [];
        $('div.accordionPanel.zero ul.bodyList li').each((id, element) => {
            result.inclusions.push($(element).text() || "");
        });
        result.authenticity_notes = $('p.certified').text() || "";
        result.seller_status = "";

        return result;
    } catch (error) {
        console.error('Error fetching or parsing the URL:', error);
        throw error; // Re-throw the error to handle it in the async call
    }
}