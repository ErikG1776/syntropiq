import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const source = path.resolve(__dirname, "../../outputs/readmission_results.json");
const targetDir = path.resolve(__dirname, "../public");
const target = path.resolve(targetDir, "readmission_results.json");

fs.mkdirSync(targetDir, { recursive: true });

if (!fs.existsSync(source)) {
  fs.writeFileSync(target, JSON.stringify({ summary: {}, timeline: [], payload_examples: {} }, null, 2));
  console.log(`Source missing: ${source}. Wrote fallback ${target}`);
  process.exit(0);
}

fs.copyFileSync(source, target);
console.log(`Copied ${source} -> ${target}`);
