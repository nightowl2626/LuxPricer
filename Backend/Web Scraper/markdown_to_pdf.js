// src/markdownToPdf.js

const { PDFDocument } = require('pdf-lib');
const fs = require('fs');
const marked = require('marked');

async function markdownToPdf(markdownText, outputPath) {
    // Convert Markdown to HTML
    const html = marked(markdownText);

    // Create a new PDF document
    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage();

    // Load the HTML content into the PDF
    const fontSize = 12;
    const fontBytes = await fetch('https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/0.8.4/fonts/Arial.ttf').then(res => res.arrayBuffer());
    const font = await pdfDoc.embedFont(fontBytes);

    let y = page.getSize().height - 40; // Start from the top of the page
    html.split('\n').forEach(line => {
        const textWidth = font.widthOfTextAtSize(line, fontSize);
        if (textWidth > page.getWidth() - 20) { // Subtract some margin
            y -= 15; // Move to the next line
        }
        page.drawText(line, {
            x: 10,
            y: y,
            size: fontSize,
            font: font,
            color: rgb(0, 0, 0),
        });
        y -= 12; // Move slightly down for the next line
    });

    // Save the PDF to output path
    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync(outputPath, pdfBytes);

    console.log(`PDF created at ${outputPath}`);
}

// Example usage:
if (require.main === module) {
    const markdownText = `
# Hello World

This is a sample Markdown text.

## Subheading

- Item 1
- Item 2
    - Subitem 1
    - Subitem 2
`;
    const outputPath = "output.pdf";
    markdownToPdf(markdownText, outputPath).catch(console.error);
}