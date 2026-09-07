/* Print geometry is physical, independent of SVG layout, theme and zoom. */
const libraryUrl = new URL('./vendor/pdf-lib-1.17.1/pdf-lib.esm.min.js', import.meta.url);
const retry = new URL(import.meta.url).searchParams.get('retry');
if (retry) libraryUrl.searchParams.set('retry', retry);
const { PDFDocument, StandardFonts, rgb, PDFName, PDFString } = await import(libraryUrl.href);

export const pointsPerMillimetre = 72 / 25.4;
export const mmToPoints = (mm) => mm * pointsPerMillimetre;
const ascii = (text) => String(text).replaceAll('±', '+/-').replaceAll('×', 'x').replace(/[^\x20-\x7e\n]/g, ' ');

export async function buildComparisonPDF(records, options = {}) {
    if (!records.length) throw new Error('There are no supported pitches to print. Choose common supported pitches.');
    const grouped = new Map();
    for (const record of records) {
        if (!(record.pitch_mm > 0) || !record.capabilities.print_pitch) continue;
        const key = record.pitch_mm.toPrecision(12);
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(record);
    }
    const pitchSheet = options.layout === 'pitches';
    const groups = pitchSheet ? [...grouped.values()].sort((a, b) => a[0].pitch_mm - b[0].pitch_mm)
        : [...new Map(records.filter((row) => row.capabilities.print_pitch).map((row) => [row.id, row])).values()].map((row) => [row]);
    const doc = await PDFDocument.create();
    doc.setTitle(pitchSheet ? 'Thread pitch reference' : 'Thread size comparison');
    doc.setSubject('Preliminary identification aid; not a thread gage or tolerance verification');
    doc.setProducer('transparent.tools physical thread model v1 / pdf-lib 1.17.1');
    const font = await doc.embedFont(StandardFonts.Helvetica);
    const bold = await doc.embedFont(StandardFonts.HelveticaBold);
    const [width, height] = options.paper === 'a4' ? [210, 297] : [215.9, 279.4];
    const side = options.side === 'internal' ? 'internal' : 'external';
    const diameterOf = (record) => record.model ? record.model[side === 'internal' ? 'internal_minor_mm' : 'major_diameter_mm'] : null;
    const rowHeight = (record) => pitchSheet ? 32 : Math.max(36, (diameterOf(record) || 0) + 24);
    // Pack physical rows without rescaling either axis. Large diameters need
    // taller rows; extra rows move to a new page, never shrink to fit.
    const pages = [];
    let rows = [], cursor = 59;
    for (const group of groups) {
        const row = { group, height: rowHeight(group[0]) };
        if (row.height > height - 65 - 59) throw new Error('This diameter is too large for the selected paper at 1:1.');
        if (rows.length && (cursor + row.height > height - 65 || (pitchSheet && rows.length === 4))) {
            pages.push(rows); rows = []; cursor = 59;
        }
        rows.push({ ...row, y: cursor }); cursor += row.height;
    }
    if (rows.length) pages.push(rows);
    const manifest = { unit: 'mm', paper: options.paper || 'letter', layout: pitchSheet ? 'pitches' : 'sizes', side, pages: [] };
    for (const [pageIndex, rows] of pages.entries()) {
        const page = doc.addPage([mmToPoints(width), mmToPoints(height)]);
        page.drawRectangle({ x: 0, y: 0, width: mmToPoints(width), height: mmToPoints(height), color: rgb(1, 1, 1) });
        const pageRecord = { width_mm: width, height_mm: height, strips: [] };
        manifest.pages.push(pageRecord);
        const line = (x1, y1, x2, y2, thickness = 0.4) => page.drawLine({
            start: { x: mmToPoints(x1), y: mmToPoints(height - y1) },
            end: { x: mmToPoints(x2), y: mmToPoints(height - y2) },
            thickness, color: rgb(0, 0, 0),
        });
        const text = (value, x, y, size = 8, strong = false) => page.drawText(ascii(value), {
            x: mmToPoints(x), y: mmToPoints(height - y), size, font: strong ? bold : font,
            color: rgb(0, 0, 0),
        });
        const wrap = (value, x, y, maxWidth = 157, size = 8) => {
            let current = '', row = 0;
            for (const word of ascii(value).split(/\s+/)) {
                const next = current ? current + ' ' + word : word;
                if (font.widthOfTextAtSize(next, size) > mmToPoints(maxWidth) && current) {
                    text(current, x, y + row * 3.8, size); current = word; row++;
                } else current = next;
            }
            if (current) text(current, x, y + row * 3.8, size);
            return row + 1;
        };
        text(pitchSheet ? 'THREAD PITCH REFERENCE' : 'THREAD SIZE COMPARISON', 15, 17, 14, true);
        text(`Thread Calculator & Identifier | ${options.paper === 'a4' ? 'A4' : 'US Letter'} | Page ${pageIndex + 1} of ${pages.length}`, 15, 23, 8);
        text('PRINT AT ACTUAL SIZE / 100%. Disable Fit, Shrink and page scaling.', 15, 31, 9, true);
        wrap('Measure both 100 mm checks before using this page. If either is wrong, fix the print settings and reprint. Align one crest beside the start line, then compare several successive crests.', 15, 37);
        wrap('Count spaces: 11 crests span 10 intervals. Paper is not a mating gage. Never force an unknown thread into a part. For an internal thread, use a measurable mating part or a suitable pitch gage.', 15, 49);
        for (const { group, y, height: rowSize } of rows) {
            const record = group.find((row) => row.model) || group[0];
            const pitch = record.pitch_mm;
            const intervals = Math.max(1, Math.floor(80 / pitch));
            const labelStep = [1, 2, 5, 10, 20, 50, 100].find((step) => step * pitch >= 7) || 100;
            const labels = group.slice(0, 3).map((row) => row.designation).join(', ') + (group.length > 3 ? ` (+${group.length - 3} other sizes)` : '');
            const pitchLabel = `Pitch ${pitch.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')} mm | ${record.tpi.toFixed(3).replace(/\.?0+$/, '')} TPI`;
            text(pitchSheet ? pitchLabel : record.designation, 15, y + 5, pitchSheet ? 9 : 11, true);
            wrap(pitchSheet ? labels : pitchLabel, 15, y + 10, pitchSheet ? 155 : 88, 7);
            const x = 25, baseline = y + 19;
            line(x, baseline, x + intervals * pitch, baseline, 0.35);
            for (let n = 0; n <= intervals; n++) {
                const major = n % labelStep === 0 || n === intervals;
                line(x + n * pitch, baseline, x + n * pitch, baseline - (major ? 3 : 1.8), 0.35);
                if (n % labelStep === 0 || (n === intervals && (n % labelStep) * pitch >= 7)) text(n, x + n * pitch - 0.6, baseline + 3, 5.5);
            }
            text('start', 15, baseline, 6);
            if (record.model) {
                const profile = record.model[side];
                const maxRadius = Math.max(...profile.map((point) => point[1]));
                for (let n = 0; n < intervals; n++) {
                    profile.slice(1).forEach(([axial, radius], i) => {
                        const [previousX, previousR] = profile[i];
                        line(x + n * pitch + previousX, baseline + 6 + maxRadius - previousR,
                            x + n * pitch + axial, baseline + 6 + maxRadius - radius, 0.3);
                    });
                }
                text(`1:1 simplified ${side} profile; not tolerance limits`, 25, baseline + 11, 6);
            } else text('Pitch ticks only; no validated actual-size pipe profile', 25, baseline + 9, 7);
            let diameter = null;
            if (!pitchSheet) {
                diameter = diameterOf(record);
                if (diameter != null) {
                    const basis = side === 'internal' ? 'BASIC INTERNAL MINOR' : 'NOMINAL EXTERNAL MAJOR';
                    text(basis, 113, y + 5, 7, true);
                    text(`${diameter.toFixed(3)} mm / ${(diameter / 25.4).toFixed(4)} in`, 113, y + 10, 8);
                    const cx = 146, top = y + 14;
                    page.drawCircle({ x: mmToPoints(cx), y: mmToPoints(height - top - diameter / 2),
                        size: mmToPoints(diameter / 2), borderWidth: 0.4, borderColor: rgb(0, 0, 0) });
                    const dimensionY = top + diameter + 3;
                    line(cx - diameter / 2, dimensionY, cx + diameter / 2, dimensionY);
                    for (const x of [cx - diameter / 2, cx + diameter / 2]) line(x, dimensionY - 1.5, x, dimensionY + 1.5);
                    text('1:1 diameter reference', 127, dimensionY + 4, 6);
                } else {
                    text('PITCH ONLY', 120, y + 8, 9, true);
                    text('Diameter not compared', 120, y + 14, 7);
                    text('Nominal pipe size is not OD', 120, y + 19, 6.5);
                }
                line(15, y + rowSize - 1, 183, y + rowSize - 1, 0.2);
            }
            pageRecord.strips.push({ id: record.id, designation: record.designation, pitch_mm: pitch, diameter_mm: diameter,
                side, bounds_mm: [15, y, 183, y + rowSize], intervals, start_mm: [x, baseline], end_mm: [x + intervals * pitch, baseline] });
        }
        const footer = height - 65;
        text('WORKSHEET', 15, footer, 8, true);
        text('Diameter: __________  units: _____  external / internal / unsure', 15, footer + 5, 8);
        text('Span: __________  intervals (spaces): _____  pitch = span / intervals', 15, footer + 10, 8);
        text('Measurement planes / hand / observations: __________________________', 15, footer + 15, 8);
        wrap('Supported nominal catalog only; pitch matches may span several families and sizes. No fit, sealing, pressure or strength verification. Wear, parallax, line width and printer resolution limit comparison.', 15, footer + 21, 173, 7);
        if (options.observations) wrap('Entered readings: ' + options.observations, 15, footer + 32, 173, 6);
        if (options.url) {
            // A clickable full-state link avoids printing an unreadably long URL.
            const annotation = doc.context.obj({ Type: 'Annot', Subtype: 'Link',
                Rect: [mmToPoints(145), mmToPoints(8), mmToPoints(195), mmToPoints(14)],
                Border: [0, 0, 0], A: { Type: 'Action', S: 'URI', URI: PDFString.of(options.url) } });
            page.node.set(PDFName.of('Annots'), doc.context.obj([doc.context.register(annotation)]));
            text('Open saved measurements', 145, height - 10, 7);
        }
        // Exact 100 mm horizontal AND vertical checks on EVERY page.
        const dimension = (x1, y1, x2, y2) => {
            line(x1, y1, x2, y2, 0.7);
            const horizontal = y1 === y2;
            for (const [x, y] of [[x1, y1], [x2, y2]]) line(x - (horizontal ? 0 : 2), y - (horizontal ? 2 : 0), x + (horizontal ? 0 : 2), y + (horizontal ? 2 : 0), 0.7);
        };
        dimension(15, height - 20, 115, height - 20);
        text('100 mm horizontal: measure between end marks', 15, height - 23, 7);
        dimension(width - 20, 65, width - 20, 165);
        page.drawText('100 mm vertical: check this direction too', { x: mmToPoints(width - 16), y: mmToPoints(height - 165), size: 7, font, rotate: { type: 'degrees', angle: 90 } });
        dimension(15, height - 10, 40.4, height - 10);
        text('1 inch (25.4 mm)', 44, height - 9, 7);
        text('transparent.tools', 145, height - 17, 7);
    }
    return { bytes: await doc.save({ useObjectStreams: false }), manifest };
}
