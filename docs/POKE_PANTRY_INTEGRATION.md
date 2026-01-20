# Poke → Pantry Tool Integration Guide

**Tool Name:** `receipt_photo_pantry_inventory`

## 📋 Complete Request Format

```json
{
  "items": [
    {
      "name": "Item Name",                    // REQUIRED - will be matched/created
      "quantity": 3,                          // REQUIRED - number to add/create
      "unit": "lb",                           // OPTIONAL - "lb", "oz", "item", "kg", etc.
      "category": "Produce",                  // OPTIONAL - "Produce", "Dairy", "Meat", etc.
      "price": 4.99,                          // OPTIONAL - triggers price history
      "expiration_date": "2026-02-15",        // OPTIONAL - ISO date string
      "notes": "Fresh from farm",             // OPTIONAL - will be appended with price history
      "receipt_number": "12345",              // OPTIONAL - receipt identifier
      "storage_location": "Fridge",           // OPTIONAL - where item is stored
      "status": "Fresh"                       // OPTIONAL - item status
    }
  ],
  "store": "Whole Foods",                     // OPTIONAL - applies to all items if not specified per item
  "purchase_date": "2026-01-20",              // OPTIONAL - ISO date, defaults to today
  "dry_run": false,                           // REQUIRED - must be false to write
  "confirm": true                             // REQUIRED - must be true to write
}
```

## ⚡ Quick Format (Minimum Required)

```json
{
  "items": [
    {"name": "Bananas", "quantity": 3}
  ],
  "dry_run": false,
  "confirm": true
}
```

## 🎯 Recommended Format for Poke

When Poke extracts items from a receipt photo, it should send:

```json
{
  "items": [
    {
      "name": "Organic Bananas",
      "quantity": 3,
      "unit": "lb",
      "price": 4.99
    },
    {
      "name": "Almond Milk",
      "quantity": 1,
      "unit": "gallon",
      "price": 5.49
    }
  ],
  "store": "Whole Foods",
  "purchase_date": "2026-01-20",
  "dry_run": false,
  "confirm": true
}
```

## 📝 Field Details

### Item Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | ✅ Yes | Item name (fuzzy matched) | `"Organic Bananas"` |
| `quantity` | number | ✅ Yes | Amount to add | `3` or `1.5` |
| `unit` | string | ⚪ Optional | Unit of measurement | `"lb"`, `"oz"`, `"item"`, `"kg"` |
| `category` | string | ⚪ Optional | Food category | `"Produce"`, `"Dairy"`, `"Meat"` |
| `price` | number | ⚪ Optional | Price (triggers history) | `4.99` |
| `expiration_date` | string | ⚪ Optional | ISO date string | `"2026-02-15"` |
| `notes` | string | ⚪ Optional | Additional notes | `"Organic from local farm"` |
| `receipt_number` | string | ⚪ Optional | Receipt ID | `"R-12345"` |
| `storage_location` | string | ⚪ Optional | Where stored | `"Fridge"`, `"Pantry"`, `"Freezer"` |
| `status` | string | ⚪ Optional | Item status | `"Fresh"`, `"To Use Soon"` |

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `store` | string | ⚪ Optional | Store name (applies to all items) |
| `purchase_date` | string | ⚪ Optional | ISO date, defaults to today |
| `dry_run` | boolean | ✅ Yes | Must be `false` to write |
| `confirm` | boolean | ✅ Yes | Must be `true` to write |

## 🔄 How Fuzzy Matching Works

When Poke sends items, the tool:

1. **Checks existing pantry items** (queries up to 100)
2. **Scores similarity** for each existing item (0-1 scale)
3. **If match ≥ 0.7:** Updates existing item quantity
4. **If match < 0.7:** Creates new item

**Examples:**
- ✅ `"Bananas"` matches `"Bananas"` → score: 1.0 → **UPDATE**
- ✅ `"Organic Bananas"` matches `"Bananas Organic"` → score: 0.8 → **UPDATE**
- ❌ `"Bananas"` vs `"Organic Bananas"` → score: 0.5 → **CREATE NEW**

## 📊 Response Format

```json
{
  "summary": "Parsed 2 item(s). Created 1 item(s) in Notion. Updated 1 existing item(s).",
  "result": {
    "items": [...],           // Processed items
    "duplicates": [...],      // Duplicates within same request
    "created": [              // Newly created items
      {
        "id": "page-id",
        "url": "https://notion.so/...",
        "name": "Almond Milk"
      }
    ],
    "updated": [              // Updated existing items
      {
        "id": "page-id",
        "url": "https://notion.so/...",
        "name": "Organic Bananas",
        "matched_with": "Bananas",
        "match_score": 0.8,
        "quantity_added": 3
      }
    ],
    "skipped_existing": [],
    "property_map": {...},
    "checked_existing": true,
    "ran_at": "2026-01-20T22:00:00Z"
  },
  "next_actions": [...],
  "errors": []
}
```

## 🎨 Price History Format

When `price` is provided, it's appended to the Notes field as:

```
Price History:
  $4.99 at Whole Foods on 2026-01-20
  $5.49 at Trader Joes on 2026-01-21

Raw: [{"price": 4.99, "date": "2026-01-20", "store": "Whole Foods"}, ...]
```

## 🚀 Poke Integration Steps

1. **Extract receipt data** from image using OCR/AI
2. **Parse items** into the format above
3. **Call MCP tool** `receipt_photo_pantry_inventory`
4. **Show response** to user:
   - "Added X items to pantry"
   - "Updated Y existing items"
   - Link to Notion page

## 💡 Tips for Poke

### Best Practices
- ✅ Always include `name` and `quantity` (minimum)
- ✅ Include `price` to track price history
- ✅ Set `store` at top level (applies to all items)
- ✅ Use `purchase_date` as today's date
- ✅ Normalize unit names (`"lb"` not `"lbs"` or `"pounds"`)

### Category Suggestions
Common categories Poke might use:
- `"Produce"` - fruits, vegetables
- `"Dairy"` - milk, cheese, yogurt
- `"Meat"` - chicken, beef, pork
- `"Seafood"` - fish, shrimp
- `"Bakery"` - bread, pastries
- `"Frozen"` - frozen foods
- `"Pantry"` - dry goods, canned items
- `"Snacks"` - chips, cookies
- `"Beverages"` - drinks, juice

### Storage Location Suggestions
- `"Fridge"` - refrigerated items
- `"Freezer"` - frozen items
- `"Pantry"` - shelf-stable items
- `"Counter"` - fruits/vegetables at room temp

## 🔍 Testing with curl

```bash
./vm/mcp_curl.sh receipt_photo_pantry_inventory '{
  "items": [
    {"name": "Test Item", "quantity": 1, "unit": "item", "price": 2.99}
  ],
  "store": "Test Store",
  "purchase_date": "2026-01-20",
  "dry_run": false,
  "confirm": true
}'
```

## ⚠️ Common Mistakes

❌ **Forgetting dry_run/confirm**
```json
{"items": [...]}  // Will fail - needs dry_run=false, confirm=true
```

❌ **Missing quantity**
```json
{"name": "Bananas"}  // Will default to 1, but explicit is better
```

❌ **Wrong date format**
```json
{"purchase_date": "01/20/2026"}  // Use ISO: "2026-01-20"
```

✅ **Correct**
```json
{
  "items": [{"name": "Bananas", "quantity": 3}],
  "dry_run": false,
  "confirm": true
}
```
