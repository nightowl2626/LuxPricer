import express from 'express';
import { create_links, parse_url, delay } from "./utils.js";
import { get_fashionphile_links, scrap_fashionphile } from "./scrap_fashionphile.js";
import { get_vestiaire_collective_links, scrap_vestiaire_collective } from "./scrap_vestiaire_collective.js";
import fs from 'fs';

const app = express();
const port = 3000;

app.get('/scrape', async (req, res) => {
    try {
        const keywords = req.query.keywords || "gucci horsebit 1955";
        let product_list = [];
        let product_scraped = [];

        const main_list = await create_links(keywords);
        const fashionphile_list = await get_fashionphile_links(main_list.fashionphile);
        const vestiaire_collective_list = await get_vestiaire_collective_links(main_list.vestiairecollective);

        product_list.push(vestiaire_collective_list);
        product_list.push(fashionphile_list);

        let product_list_flat = product_list.flat(1).slice(0, 3);

        const results = await Promise.all(product_list_flat.map(url => parse_url(url)));

        for (const web_page of results) {
            if (web_page.source_platform == "Fashiophile") {
                console.log(web_page.listing_url);
                let temporary_result = await scrap_fashionphile(web_page.listing_url);
                product_scraped.push(temporary_result);
                console.log('done');
            } else if (web_page.source_platform == "Vestiaire Collective") {
                console.log(web_page.listing_url);
                let temporary_result = await scrap_vestiaire_collective(web_page.listing_url);
                product_scraped.push(temporary_result);
                console.log('done');
            }
            await delay(3500);
        }

        console.log(product_scraped);
        const product_scraped_json = JSON.stringify(product_scraped, null, 2);

        fs.writeFile('./data/product_scraped.json', product_scraped_json, (err) => {
            if (err) throw err;
            console.log('Saved as ./data/product_scraped.json');
        });

        res.status(200).json(product_scraped_json);
    } catch (error) {
        console.error('Error scraping URLs:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});