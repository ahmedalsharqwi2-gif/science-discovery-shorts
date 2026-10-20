import {defineConfig} from 'vite';
import {createRequire} from 'node:module';
const motionCanvas = createRequire(import.meta.url)('@motion-canvas/vite-plugin').default;
export default defineConfig({plugins:[motionCanvas({project:'./motion/project.ts'})],build:{outDir:'dist/motion'}});
