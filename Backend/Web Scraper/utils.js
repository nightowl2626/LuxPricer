import path from 'path';
import fs from 'fs';

export async function get_status(url) {
    try {
        const response = await fetch(url);
        if (response.status === 200) {
            return { url, status: "cheerio" };
        } else {
            // You might want to handle other statuses or throw an error
            return { url, status: `playwright` };
        }
    } catch (error) {
        console.error(`Failed to fetch ${url}:`, error);
        return { url, status: "Error" };
    }
}

export function parse_url(url) {
    const parsedUrl = new URL(encodeURI(url).replace(/%EF%BB%BF/g, ""));
    const pathnameParts = parsedUrl.pathname.split('/').filter(part => part.length > 0);

    const websiteName = parsedUrl.hostname;

    let articleId;
    let source_plateform;

    if (websiteName.includes('vestiairecollective.com')) {
        articleId = pathnameParts.pop().replace(".shtml", "").split("-").pop();
        source_plateform = "Vestiaire Collective";
    } else if (websiteName.includes('fashionphile.com')) {
        articleId = pathnameParts.pop().split("-").pop(); // Assuming the ID is in the third position
        source_plateform = "Fashiophile";
    } else {
        articleId = 'Unknown';
        source_plateform = "Uknown";
    }
    return {
        listing_id: articleId,
        listing_url: url,
        source_platform: source_plateform
    };
}

export async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export async function get_links_sample() {
    let local_path = './Backend/JavaScript/links_sample/'
    
    const links_sample_path = await fs.promises.readdir(local_path);
    const all_links = await Promise.all(links_sample_path.map(async (text) => {
        const filePath = path.join(local_path, text);
        try {
            const data = await fs.promises.readFile(filePath, 'utf8');
            return data.split('\n');
        } catch (err) {
            console.error(err);
            return [];
        }
    }));
    return all_links.flat(1);
};

export function create_links(input) {
    // Encode the input string for URL use
    const fashionphile_encode = encodeURIComponent(input);

    // Create the first link
    const fashionphile_link = `https://www.fashionphile.com/shop?search=${fashionphile_encode}`;

    const vestiaire_collective_encode = encodeURIComponent(input).replace(/%20/g, '+');

    // Create the second link
    const vestiaire_collective_link = `https://www.vestiairecollective.com/search/?q=${vestiaire_collective_encode}`;

    return {
        fashionphile: fashionphile_link,
        vestiairecollective: vestiaire_collective_link
    };
}