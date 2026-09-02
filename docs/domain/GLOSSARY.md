# Domain Glossary

## Purpose

This glossary defines the terms the helper must use when reasoning about early-league currency generation and trading.

The definitions are intentionally grounded in the player experience, not in abstract market theory.

---

## Currency Exchange

Definition:
The in-game system used to exchange one type of currency for another instantly through the market, without direct player-to-player item trading.

Meaning in gameplay:
This is the currency trading interface the player uses to convert between different currency types. It is a key source of market price information and a basic way to move value from one form to another.

Project use:
This is the clearest baseline for currency conversion logic, chaos normalization, and exchange-rate checks.

Visual evidence:
See [screenshots/Currency-Exchange-Window.webp](screenshots/Currency-Exchange-Window.webp).

Important note:
This system is for currencies only. Equippable items such as weapons and body armour are not traded through the Currency Exchange and instead require the Trade Site and stash tabs.

Liquidity note:
People tend to buy and sell items with Exalted Orbs, Divine Orbs, and Chaos Orbs, so trades are often found faster using these. However, less common currency types can still be used to make exchanges with more favourable rates when the spread is good.

---

## Currency Exchange Tabs

Definition:
The tabs on the left side of the Currency Exchange that filter which item categories are available for exchange.

Meaning in gameplay:
Each tab narrows the list to a specific category of tradeable currency and related market items, helping the player focus on the right type of value for the current play session.

Project use:
This defines the market category filters used by the helper and later supports category-aware recommendation logic.

Visual evidence:
See the screenshot for the Currency Exchange window with the left-side tabs visible.

Tab categories:
- Owned: Shows all currency-market-tradable items currently owned by the player.
- Currency: Shows basic currency items such as Chaos Orbs, Exalted Orbs, and Divine Orbs.
- Delirium: Shows Distilled Emotions, Simulacrum Splinters, and Simulacrums.
- Breach: Shows Breach Splinters, Breachstones, and Catalysts.
- Fragments: Shows Ritual Fragments, Ultimatum Fragments, and Pinnacle Fragments.
- Expedition: Shows Artifacts and Exotic Coinage.
- Essences: Shows Essences and Greater Essences.
- Runes: Shows socketable Runes.
- Omens: Shows Omens, which can be acquired through Ritual.
- Soul Cores: Shows Soul Cores, which can be acquired through the Trial of Chaos.

---

## Market

Definition:
The game’s overall trade environment, which is conceptually one system but has two main access paths: the Currency Exchange for currency and the item market for non-currency goods.

Meaning in gameplay:
The player can trade different kinds of value through different entry points, but both are part of the same broader market. Currency-only transactions go through the Currency Exchange, while non-currency items and gear go through the item/trade side of the market.

Project use:
This distinction is important for the helper. Currency logic and item logic should be treated as two views of the same market, not two unrelated systems.

Important note:
The Currency Exchange is the currency-focused entry point. The item market is the entry point for weapons, armour, gear, and any other items that cannot be exchanged through the Currency Exchange.

This keeps terminology clear:
- Currency market = currency conversion and exchange behaviour
- Item market = trade-site and stash-based trading for non-currency items
- Market = the combined system behind both flows

---

## Market Ratio

Definition:
The ratio displayed at the top of the Currency Exchange window that reflects how the market is valuing a currency pair and how favourable the current trade is.

Meaning in gameplay:
The player can hover over the Market Ratio and press Alt to reveal more detail, including Available Trades and Competing Trades. This gives a rapid view of how liquid the market is and whether a trade is relatively strong or weak compared with nearby offers.

Project use:
This is directly relevant to bulk trading margins and market depth. If we can capture or estimate this ratio from live market data, it helps identify whether a currency exchange is worth doing at scale.

Visual evidence:
See [screenshots/market-ratio.png](screenshots/market-ratio.png).

Important note:
This is not just a static value. It is a market-readout that helps the player decide whether to act now, wait, or choose a different trade path. It is especially useful when evaluating bulk exchange margins and competing offers.

---

## In-Game Market Window

Definition:
The in-game market interface used to search for non-currency items and trade them through the game’s item market system.

Meaning in gameplay:
This is the player-facing market window that lets the player search items. It is the in-game shell around the external trade platform at https://www.pathofexile.com/trade2/.

Project use:
This is the relevant entry point for item trading, gear pricing, and non-currency market analysis. It should be treated as the item-market side of the broader market system, not as a separate unrelated market.

Visual evidence:
See [screenshots/PoE_2_Market_Window.png](screenshots/PoE_2_Market_Window.png).

Important note:
This is the non-currency side of the market. It is the path used for searchable items, gear, and tradeable goods that cannot be exchanged through the Currency Exchange system.

---

## In-Game Vendor

Definition:
An NPC or vendor in the world that sells items or services using in-game currency such as gold, rather than the Currency Exchange market system.

Meaning in gameplay:
This is the ordinary in-game vendor interaction the player uses to buy utility items, scrolls, and other non-tradeable goods. It is not the same as a player-to-player or Currency Exchange trade.

Project use:
This defines the vendor-driven pricing path used to compare NPC buying and selling against market opportunities.

Visual evidence:
See [screenshots/ROG-NPC-Example-Vendor-Wisdomscroll.png](screenshots/ROG-NPC-Example-Vendor-Wisdomscroll.png).

Example:
A Wisdom Scroll costs 25 gold from an in-game NPC vendor. Gold is not a tradeable currency in the same way as Currency Exchange materials, so this is a different trading channel.

Naming guidance:
For clarity, we should distinguish between:
- Currency Exchange trade: a market-based trade between players or market listings
- In-game vendor trade: a vendor transaction with an NPC
- Buyer: the actor buying an item or currency
- Seller: the actor selling an item or currency

For this project, the most precise term is:
- Vendor Trade = a player purchase from an NPC vendor
- Market Trade = a trade through the Currency Exchange or player market channel

This keeps the terminology precise and avoids confusion between player-market trading and vendor purchasing.

---

## Market Value

Definition:
The value an item or currency has in the current market.

Meaning in gameplay:
This is the price the player sees when checking what something is worth.

---

## Vendor Cost

Definition:
The price an NPC vendor charges or pays for an item.

Meaning in gameplay:
This is the in-game vendor path, usually using gold or another non-market currency.

---

## Vendor-to-Market Spread

Definition:
The difference between a vendor price and the market value of the same item or currency.

Meaning in gameplay:
A positive spread means there may be profit in buying from the vendor and selling on the market, or vice versa.

---

## Buy Low / Sell High

Definition:
The core trade loop: buy at a lower effective price and sell or convert at a higher one.

Meaning in gameplay:
This is the actual early-league profit loop the helper should support.

---

## Conversion

Definition:
Changing one currency or item into another through the market or a trade route.

Meaning in gameplay:
This is how the player moves value between currency types to reach a more useful form.

---

## Affordability

Definition:
Whether the player can actually enter a trade with the capital they currently have.

Meaning in gameplay:
This matters most at league start, when capital is limited.

---

## Fresh-Start Loop

Definition:
The early-game strategy of building currency using low-risk, affordable, repeatable trades.

Meaning in gameplay:
This is the project’s target loop for a fresh character: small wins, low risk, steady capital growth.

---

## Decision Rule

The helper should rank trades by affordability and repeatability first, not by maximum item price alone.

The real rule is:
- affordable first
- repeatable second
- profitable third
- expensive plays only when the capital and route still make sense
