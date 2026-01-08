# BrickLink Minifigure Manager - Usage Diagram

## System Overview

```mermaid
flowchart TD
    Start([Start]) --> Setup{Setup Complete?}

    Setup -->|No| GetAPI[Get BrickLink API Credentials]
    GetAPI --> CreateEnv[Create .env file with credentials]
    CreateEnv --> InstallDeps[Install Dependencies:<br/>requests, requests-oauthlib, python-dotenv]
    InstallDeps --> Ready

    Setup -->|Yes| Ready[Ready to Use]

    Ready --> Import[IMPORT: XML Inventory File]
    Import --> Parse[Parse XML to extract minifigures]
    Parse --> FetchPrices[Fetch Prices from BrickLink API]

    FetchPrices --> Markup{Apply Markup?}
    Markup -->|Yes| AddMarkup[Add percentage markup<br/>Default: 10%]
    Markup -->|No| NoMarkup[Use original prices]

    AddMarkup --> Export
    NoMarkup --> Export

    Export[EXPORT Results]

    Export --> ExportXML[Export to XML<br/>BrickLink Mass Upload Format<br/>with markup applied]
    Export --> ExportJSON[Export to JSON<br/>Simplified format]
    Export --> ExportDetailed[Export Detailed JSON<br/>Full price data]

    ExportXML --> Upload[Upload to BrickLink Store]

    style Setup fill:#ffeb99
    style Import fill:#99ccff
    style Export fill:#99ff99
    style Markup fill:#ffcc99
```

## Detailed Workflow

### 1. Initial Setup
```mermaid
sequenceDiagram
    participant User
    participant Script
    participant BrickLink

    User->>BrickLink: Register API Application
    BrickLink->>User: Provide 4 Credentials
    User->>Script: Create .env file
    Note over Script: BRICKLINK_CONSUMER_KEY<br/>BRICKLINK_CONSUMER_SECRET<br/>BRICKLINK_TOKEN_KEY<br/>BRICKLINK_TOKEN_SECRET
    User->>Script: Install dependencies (pip install)
```

### 2. Import Process
```mermaid
flowchart LR
    A[XML Inventory File<br/>Minifigures.xml] --> B[Parse XML]
    B --> C{Extract Items}
    C --> D[Item ID]
    C --> E[Quantity]
    C --> F[Condition N/U]
    C --> G[Color]

    D --> H[Validated Minifigures List]
    E --> H
    F --> H
    G --> H

    style A fill:#99ccff
    style H fill:#99ff99
```

### 3. Price Fetching with Markup
```mermaid
flowchart TD
    Start[For Each Minifigure] --> API[Call BrickLink API]
    API --> Check{Price Found?}

    Check -->|Yes| GetAvg[Get Average Price]
    Check -->|No| TryNew{Condition = Used?}

    TryNew -->|Yes| FallbackNew[Try New Condition]
    TryNew -->|No| NoPriceData[No Price Data]

    FallbackNew --> GetAvg
    GetAvg --> Markup[Apply Markup Percentage]

    Markup --> Example[Example:<br/>Avg Price: $10.00<br/>Markup: 10%<br/>Final Price: $11.00]

    Example --> Store[Store Result]
    NoPriceData --> Store

    Store --> More{More Items?}
    More -->|Yes| Start
    More -->|No| Done[Complete]

    style Markup fill:#ffcc99
    style Example fill:#ffffcc
```

### 4. Export Process
```mermaid
flowchart TD
    Results[Price Results<br/>with Markup Applied] --> Export{Export Format}

    Export --> XML[XML Export]
    Export --> JSON[JSON Export]
    Export --> Detail[Detailed JSON]

    XML --> XMLContent["&lt;INVENTORY&gt;<br/>&lt;ITEM&gt;<br/>&lt;PRICE&gt;markup applied&lt;/PRICE&gt;<br/>&lt;QTY&gt;...&lt;/QTY&gt;<br/>&lt;CONDITION&gt;...&lt;/CONDITION&gt;<br/>&lt;ITEMID&gt;...&lt;/ITEMID&gt;<br/>&lt;/ITEM&gt;<br/>&lt;/INVENTORY&gt;"]

    JSON --> JSONContent["{<br/>  minifig_number: 'sw0001',<br/>  amount: 1,<br/>  average_price: 10.50,<br/>  condition: 'N'<br/>}"]

    Detail --> DetailContent["Full API Response<br/>+ avg_price<br/>+ min/max prices<br/>+ quantity available<br/>+ error messages"]

    XMLContent --> BLUpload[Upload to BrickLink<br/>Mass Upload Tool]

    style Results fill:#99ff99
    style XMLContent fill:#ffe6e6
    style JSONContent fill:#e6f3ff
    style DetailContent fill:#f0e6ff
    style BLUpload fill:#ffccff
```

## Command Examples

### Basic Usage
```bash
# Use default Minifigures.xml file
python main.py

# Specify custom XML file
python main.py --xml inventory.xml

# Show setup instructions
python main.py --setup
```

### Filtering Options
```bash
# Get only new condition prices
python main.py --xml minifigures.xml --condition N

# Get only used condition prices
python main.py --xml minifigures.xml --condition U
```

### Export with Markup
```bash
# Export with default 10% markup
python main.py --xml minifigures.xml --export prices

# Export with custom 15% markup
python main.py --xml minifigures.xml --export prices --markup 15

# Export with 20% markup
python main.py --xml minifigures.xml --export mystore --markup 20
```

### Debug Mode
```bash
# Enable debug output to see API calls
python main.py --xml minifigures.xml --debug
```

## Price Calculation Flow

```mermaid
flowchart LR
    subgraph "BrickLink API"
        API[Average Price<br/>$10.00]
    end

    subgraph "Markup Calculation"
        Markup[Markup %<br/>Default: 10%]
        Calc[Price × 1.10]
    end

    subgraph "Final Price"
        Final[Selling Price<br/>$11.00]
    end

    API --> Calc
    Markup --> Calc
    Calc --> Final

    Final --> XML[XML Export<br/>Ready for BrickLink]

    style API fill:#99ccff
    style Markup fill:#ffcc99
    style Final fill:#99ff99
    style XML fill:#ff9999
```

## File Flow Summary

```mermaid
flowchart LR
    Input["INPUT<br/>📄 Minifigures.xml<br/>(Your inventory)"] --> Script["🔧 main.py<br/>+<br/>🔑 .env"]

    Script --> Out1["OUTPUT<br/>📄 prices.xml<br/>(with markup)"]
    Script --> Out2["OUTPUT<br/>📄 prices.json<br/>(simplified)"]
    Script --> Out3["OUTPUT<br/>📄 prices_detailed.json<br/>(full data)"]

    Out1 --> BL["📤 Upload to<br/>BrickLink Store"]

    style Input fill:#99ccff
    style Script fill:#ffffcc
    style Out1 fill:#ff9999
    style Out2 fill:#99ff99
    style Out3 fill:#e6ccff
    style BL fill:#ffccff
```

## Key Features

### Import
- Read BrickLink XML inventory files
- Extract minifigure data (ID, quantity, condition, color)
- Support for both New (N) and Used (U) conditions

### Price Fetching
- OAuth1 authentication with BrickLink API
- Fetch average prices, min/max ranges
- Automatic fallback from Used to New prices if needed
- Rate limiting (0.1s delay between requests)

### Markup Application
- Configurable markup percentage (default: 10%)
- Applied during export to XML
- Helps calculate selling prices

### Export Formats

| Format | Filename | Purpose | Markup Applied |
|--------|----------|---------|----------------|
| XML | `prices.xml` | BrickLink Mass Upload | ✅ Yes |
| JSON | `prices.json` | Simplified data (minifig, qty, price) | ❌ No (shows original) |
| Detailed JSON | `prices_detailed.json` | Full API response with all price data | ❌ No (shows original) |

## Typical Use Case

1. **Export** your BrickLink inventory as XML
2. **Run script** to fetch current market prices
3. **Apply markup** (10-20%) for profit margin
4. **Export** to BrickLink Mass Upload XML format
5. **Import** back to BrickLink to update store prices automatically

## Notes

- XML export includes markup for direct upload to your store
- JSON exports show original API prices (no markup)
- Markup is only applied in the XML export for BrickLink upload
- Use higher markup for rare/valuable items
- Default 10% markup is a typical reseller margin
