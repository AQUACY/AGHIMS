# Fix Quasar ESM Error on VM

## Problem
When running `npm install` or `npm run dev` on the VM, you get:
```
Error: Dynamic require of "quasar/wrappers" is not supported
```

## Cause
Quasar is trying to use ESM (ES Modules) format, but `quasar.config.js` is using CommonJS (`require`).

## Solution

### Option 1: Clean and Reinstall (Recommended)

```bash
cd /home/administrator/Desktop/AGHIMS/frontend

# Clean Quasar cache
npx quasar clean

# Remove node_modules and package-lock
rm -rf node_modules package-lock.json

# Reinstall dependencies
npm install
```

### Option 2: If Option 1 Doesn't Work

The `quasar.config.js` has been updated to use ESM format. If you still get errors:

1. **Check Node.js version:**
   ```bash
   node --version
   ```
   Should be Node.js 18+ (as specified in package.json)

2. **Clean temporary files:**
   ```bash
   cd /home/administrator/Desktop/AGHIMS/frontend
   npx quasar clean --qconf
   rm -f quasar.config.js.temporary.compiled.*.mjs
   ```

3. **Verify quasar.config.js is ESM:**
   ```bash
   head -5 quasar.config.js
   ```
   Should show:
   ```javascript
   import { configure } from 'quasar/wrappers';
   export default configure(function (ctx) {
   ```

4. **Reinstall:**
   ```bash
   npm install
   ```

### Option 3: Force CommonJS (Alternative)

If ESM continues to cause issues, you can force CommonJS by:

1. **Rename config file:**
   ```bash
   mv quasar.config.js quasar.config.cjs
   ```

2. **Update package.json to specify config:**
   ```json
   {
     "quasar": {
       "configFile": "quasar.config.cjs"
     }
   }
   ```

   However, this is not recommended as Quasar prefers ESM for newer versions.

## Verification

After fixing, test with:
```bash
npm run dev
```

Should start without errors.

## Common Issues

### Issue: "Cannot find module 'quasar/wrappers'"
**Solution:** Make sure `@quasar/app-vite` is installed:
```bash
npm install @quasar/app-vite --save-dev
```

### Issue: "SyntaxError: Cannot use import statement outside a module"
**Solution:** Ensure `quasar.config.js` uses ESM syntax (which we've updated).

### Issue: Still getting ESM errors after fix
**Solution:** 
1. Delete `node_modules` and `package-lock.json`
2. Clear npm cache: `npm cache clean --force`
3. Reinstall: `npm install`

## Prevention

To avoid this issue in the future:
- Keep `quasar.config.js` in ESM format (using `import`/`export`)
- Don't add `"type": "module"` to `package.json` unless necessary
- Use Node.js 18+ as specified in `package.json`

