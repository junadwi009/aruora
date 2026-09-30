import {defineConfig} from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
 plugins:[react(),tailwindcss()],
 server:{host:true,port:5173,proxy:{"/api":{target:process.env.API_PROXY_TARGET||"http://127.0.0.1:5050",changeOrigin:false}}},
 test:{environment:"jsdom",globals:true,setupFiles:["./src/test-setup.ts"],include:["src/**/*.{test,spec}.{ts,tsx}"]}
});
