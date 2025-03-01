import { config } from "@eslint/eslintrc";
import eslint from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import nextjsReact from "eslint-config-next/react";
import nextjs from "eslint-config-next";

const { FlatCompat } = config;
const compat = new FlatCompat();

export default [
  {
    ignores: ["**/.next/**"],
  },
  eslint.configs.recommended,
  ...compat.extends("next/core-web-vitals"),
  {
    files: ["**/*.ts", "**/*.tsx"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off"
    }
  }
];
