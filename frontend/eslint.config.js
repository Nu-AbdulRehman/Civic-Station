import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage", "src/api/types.ts"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      // FR-FE-012: the typed client is the only module that issues HTTP.
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Use src/api/client.ts; it is the only module that issues HTTP." },
      ],
    },
  },
  {
    files: ["src/api/client.ts", "tests/**"],
    rules: { "no-restricted-globals": "off" },
  },
);
