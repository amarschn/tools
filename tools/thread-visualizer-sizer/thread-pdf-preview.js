/* Render only this tool's generated PDF. Loaded after an explicit preview request. */
const assetUrl = (filename) => {
    const url = new URL('./vendor/pdfjs-dist-6.3.289/' + filename, import.meta.url);
    const retry = new URL(import.meta.url).searchParams.get('retry');
    if (retry) url.searchParams.set('retry', retry);
    return url.href;
};
const { getDocument, GlobalWorkerOptions } = await import(assetUrl('pdf.min.mjs'));
GlobalWorkerOptions.workerSrc = assetUrl('pdf.worker.min.mjs');

export async function createPDFPreview(bytes) {
    // PDF.js transfers the buffer to its worker. Preserve the download bytes.
    const loading = getDocument({ data: bytes.slice(), useSystemFonts: true, isEvalSupported: false });
    let doc;
    try { doc = await loading.promise; }
    catch (error) { await loading.destroy(); throw error; }
    let rendering = null;
    let disposed = false;
    let sequence = 0;
    return {
        pages: doc.numPages,
        async render(number, canvas, width) {
            if (disposed) return;
            const current = ++sequence;
            if (rendering) {
                rendering.cancel();
                await rendering.promise.catch(() => {});
            }
            const page = await doc.getPage(number);
            if (disposed || current !== sequence) return;
            const natural = page.getViewport({ scale: 1 });
            const viewport = page.getViewport({ scale: Math.min(1.5, width / natural.width) });
            const resolution = Math.min(devicePixelRatio || 1, 2);
            canvas.width = Math.ceil(viewport.width * resolution);
            canvas.height = Math.ceil(viewport.height * resolution);
            rendering = page.render({ canvasContext: canvas.getContext('2d'), viewport,
                transform: resolution === 1 ? null : [resolution, 0, 0, resolution, 0, 0] });
            await rendering.promise;
            const content = await page.getTextContent();
            if (disposed || current !== sequence) return;
            return content.items.map((item) => item.str || '').join(' ');
        },
        async destroy() { disposed = true; rendering?.cancel(); await loading.destroy(); },
    };
}
