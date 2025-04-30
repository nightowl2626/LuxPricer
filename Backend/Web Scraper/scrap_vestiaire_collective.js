import playwright from 'playwright';
import * as cheerio from 'cheerio';

export async function get_vestiaire_collective_links(url){
      const vestiaire_collective_link = [];
      const browser = await playwright.chromium.launch({ headless: false });
      const context = await browser.newContext({
        // Set the language and country to English (US)
        extraHTTPHeaders: {
          'Accept-Language': 'en-US,en;q=0.9',
          'X-Forwarded-For': '192.168.1.1'
        },
        locale: 'en-US',
        // Set the geolocation to the US
        geolocation: {
          latitude: 37.7749,
          longitude: -122.4194
        },
        // Grant the 'geolocation' permission
        permissions: ['geolocation']
      });
    // await context.clearCookies();
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForSelector('button.pagination-button_paginationButton__qXLDH', { timeout: 10000 });
    await page.mouse.wheel(0, 10000); // TODO: Why does it not scroll?
    await page.waitForTimeout(550);
    const content = await page.content();
    const $ = cheerio.load(content);
    
    $('a.product-card_productCard__image__zvd4m').each((id, element) =>{
      vestiaire_collective_link.push($(element).attr('href'));
    });
    const result = vestiaire_collective_link.map(data => 'https://www.vestiairecollective.com/' + data);
    await browser.close();
    return result;
};

export async function scrap_vestiaire_collective(url){
    const result = {};
    const browser = await playwright.chromium.launch({ headless: false });
    const context = await browser.newContext({
        // Set the language and country to English (US)
        extraHTTPHeaders: {
          'Accept-Language': 'en-US,en;q=0.9',
          'X-Forwarded-For': '192.168.1.1'
        },
        locale: 'en-US',
        // Set the geolocation to the US
        geolocation: {
          latitude: 37.7749,
          longitude: -122.4194
        },
        // Grant the 'geolocation' permission
        permissions: ['geolocation']
      });
    // await context.clearCookies();
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'load' });

    const content = await page.content();
    const $ = cheerio.load(content);
    const next_data_txt = $('script#__NEXT_DATA__').text();
    const next_data = JSON.parse(next_data_txt);

    let size_details =  next_data.props.pageProps.dehydratedState.queries[6].state.data.measurements || [];

    if (size_details !== ""){
        size_details = size_details.map(data => (data.name + ": " + data.value));
    };
        
    result.listing_id = "";
    result.listing_url = url;
    result.listing_name = next_data.props.pageProps.dehydratedState.queries[6].state.data.name || "";
    result.source_plateform = "Vestiaire Collective";
    result.listing_price = next_data.props.pageProps.dehydratedState.queries[6].state.data.price.cents/100 || "";
    result.currency = next_data.props.pageProps.dehydratedState.queries[6].state.data.buyerFees[0].cost.currency || "";
    result.location = next_data.props.pageProps.dehydratedState.queries[6].state.data.seller.country || "";
    result.condition_rating = next_data.props.pageProps.dehydratedState.queries[6].state.data.condition.id || ""; // Note 5 is the worse condition
    result.condition_description = next_data.props.pageProps.dehydratedState.queries[6].state.data.condition.description || "";
    result.item_details = {
        category: next_data.props.pageProps.dehydratedState.queries[6].state.data.category.name || "",
        designer: next_data.props.pageProps.product.brand.name || "",
        model: next_data.props.pageProps.product.model.name || "",
        item_description: next_data.props.pageProps.dehydratedState.queries[6].state.data.description || "",
        size: size_details,
        material: next_data.props.pageProps.dehydratedState.queries[6].state.data.material.name || "",
        color: next_data.props.pageProps.dehydratedState.queries[6].state.data.color.name || ""
    };
    result.inclusions = [];
    result.authenticity_notes = "Optional quality control and authentication";
    result.seller_status = next_data.props.pageProps.product.seller.badges || []; 

    await browser.close();

    return result;
    };