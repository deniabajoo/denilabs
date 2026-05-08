# 📘 Walkthrough: End-to-End SPK Discount Approval System
## Odoo 19 Community — PT Indopora (Anti Gravity)
### Author: Ikhwanudin Gifari — PT Indopora

---

## 1. Arsitektur Sistem

### 1.1 Module Dependency

```mermaid
graph TD
    subgraph "Odoo Core"
        SALE[sale]
        SALE_STOCK[sale_stock]
        SALE_MGMT[sale_management]
        STOCK[stock]
        ACCOUNT[account]
        MAIL[mail]
    end

    subgraph "Custom Modules"
        APPROVAL["gifari_sale_discount_approval<br/><i>v19.0.2.0.0</i>"]
        SPK["gifari_product_discount_recommendation<br/><i>v19.0.1.0.0</i>"]
    end

    APPROVAL --> SALE
    APPROVAL --> SALE_STOCK
    APPROVAL --> SALE_MGMT
    APPROVAL --> MAIL

    SPK --> SALE
    SPK --> SALE_STOCK
    SPK --> SALE_MGMT
    SPK --> STOCK
    SPK --> ACCOUNT
    SPK --> APPROVAL
```

### 1.2 Arsitektur Model & Relasi

```mermaid
erDiagram
    SALE_ORDER ||--o{ SALE_ORDER_LINE : "order_line"
    SALE_ORDER ||--o{ APPROVAL_LOG : "approval_log_ids"
    SALE_ORDER }o--|| APPROVAL_LEVEL : "current_approval_level_id"

    APPROVAL_LEVEL }o--o{ RES_USERS : "approver_ids"
    APPROVAL_LEVEL }o--o{ RES_USERS : "escalate_to_ids"

    APPROVAL_LOG }o--|| APPROVAL_LEVEL : "level_id"
    APPROVAL_LOG }o--|| RES_USERS : "user_id"
    APPROVAL_LOG }o--o| RES_USERS : "delegated_to_id"

    SALE_ORDER_LINE }o--o| SPK_SCORE : "spk_score_id"
    SPK_SCORE }o--|| PRODUCT : "product_id"

    SPK_CRITERION ||--|| RES_COMPANY : "company_id"
    SPK_SCORE ||--|| RES_COMPANY : "company_id"

    SALE_ORDER {
        selection approval_state
        many2one current_approval_level_id
        datetime approval_deadline
        boolean discount_locked
        boolean is_sla_breached
        float effective_max_discount
    }

    APPROVAL_LEVEL {
        float min_discount
        float max_discount
        float sla_hours
        boolean can_delegate
        boolean send_email_notification
        selection approval_mode
    }

    APPROVAL_LOG {
        selection action
        float old_max_discount
        float new_max_discount
        many2one delegated_to_id
    }

    SPK_SCORE {
        float saw_score
        selection recommendation_level
        float recommended_discount_percent
        float raw_stock_age
        float raw_overstocking_ratio
        float raw_margin_safety
        float raw_demand_trend
    }

    SPK_CRITERION {
        string code
        selection criterion_type
        float weight
    }
```

---

## 2. Flow Utama Sistem

### 2.1 Approval Workflow — State Machine

```mermaid
stateDiagram-v2
    [*] --> none: SO Created

    none --> pending: Confirm SO<br/>(discount > threshold)
    none --> confirmed: Confirm SO<br/>(no approval needed)

    pending --> approved: Final Approval
    pending --> rejected: Rejected
    pending --> pending: Advance Level<br/>or Delegate
    pending --> none: Cancel Approval

    rejected --> pending: Re-submit
    rejected --> none: Cancel

    approved --> confirmed: Auto-confirm SO
    confirmed --> [*]

    note right of pending
        SLA countdown active
        Cron checks hourly
        Escalation on breach
    end note
```

### 2.2 Full End-to-End Flow

```mermaid
flowchart TD
    A["👤 Salesperson<br/>Buat Sales Order"] --> B["📋 Pilih Produk"]
    B --> C{"SPK Score<br/>tersedia?"}
    C -->|Ya| D["📊 Tampilkan<br/>Rekomendasi Diskon SPK"]
    C -->|Tidak| E["⚠️ No Recommendation"]
    D --> F["✏️ Input Diskon<br/>(sesuai/tidak dgn SPK)"]
    E --> F

    F --> G["🔘 Klik Confirm"]
    G --> H{"Discount ><br/>threshold?"}
    H -->|Tidak| I["✅ SO Confirmed<br/>Langsung"]
    H -->|Ya| J["📨 Submit for Approval"]

    J --> K["📧 Notif: Activity + Email"]
    K --> L["⏰ SLA Countdown Mulai"]

    L --> M{"Approver<br/>Action?"}
    M -->|Approve| N{"Level<br/>terakhir?"}
    M -->|Reject| O["❌ Rejected"]
    M -->|Delegate| P["🔄 Delegasi ke User Lain"]
    M -->|SLA Breach| Q["⚠️ Eskalasi Otomatis"]

    N -->|Ya| R["✅ Final Approved"]
    N -->|Tidak| S["⬆️ Advance ke Level Berikutnya"]
    S --> K

    R --> T["🔒 Lock Discount"]
    T --> U["✅ SO Auto-Confirmed"]

    O --> V{"Salesperson<br/>Action?"}
    V -->|Revisi & Resubmit| J
    V -->|Cancel| W["🚫 Kembali ke None"]

    P --> M
    Q --> M
```

---

## 3. SAW Scoring Engine

### 3.1 Alur Komputasi SAW

```mermaid
flowchart LR
    A["🕐 Cron Harian<br/>atau Manual Wizard"] --> B["Ambil Produk Aktif<br/>(sale_ok = True)"]
    B --> C["Hitung Raw Values<br/>per Produk"]

    C --> D["C1: Stock Age<br/>(on_hand / daily_demand)"]
    C --> E["C2: Overstocking Ratio<br/>(on_hand / monthly_demand)"]
    C --> F["C3: Margin Safety<br/>((price - cost) / price × 100)"]
    C --> G["C4: Demand Trend<br/>(total_sold_90d / 90)"]

    D & E & F & G --> H["Normalisasi SAW"]
    H --> I["Benefit: x / max_x"]
    H --> J["Cost: min_x / x"]

    I & J --> K["Weighted Sum<br/>V = Σ(w × r)"]
    K --> L{"SAW Score?"}

    L -->|"≥ 0.80"| M["🔴 HIGH<br/>Diskon 25%"]
    L -->|"≥ 0.60"| N["🟡 MEDIUM<br/>Diskon 15%"]
    L -->|"≥ 0.40"| O["🔵 LOW<br/>Diskon 7%"]
    L -->|"< 0.40"| P["⚪ NONE<br/>Diskon 0%"]
```

### 3.2 Bobot Default Kriteria

| # | Kriteria | Code | Tipe | Bobot | Interpretasi |
|---|----------|------|------|-------|-------------|
| 1 | Stock Age | `stock_age` | Cost | 30% | Stok makin tua → makin prioritas diskon |
| 2 | Overstocking | `overstocking_ratio` | Cost | 25% | Overstock → prioritas diskon |
| 3 | Margin Safety | `margin_safety` | Benefit | 25% | Margin tinggi → aman diberi diskon |
| 4 | Demand Trend | `demand_trend` | Benefit | 20% | Demand tinggi → less urgent diskon |

---

## 4. Skenario End-to-End

### Skenario 1: Approval Standar (Single Level, Approve)

```mermaid
sequenceDiagram
    actor Sales as Salesperson
    participant SO as Sales Order
    participant SPK as SPK Engine
    participant SYS as Approval System
    actor Approver as Supervisor

    Sales->>SO: Buat SO, tambah produk
    SO->>SPK: Lookup SPK Score
    SPK-->>SO: Rec. Discount 15% (MEDIUM)
    Sales->>SO: Input discount 18%
    Sales->>SO: Klik "Confirm"

    SO->>SYS: _needs_approval() → True
    SYS->>SYS: _submit_for_approval()
    SYS->>Approver: 📧 Email + 🔔 Activity
    SYS->>SO: State = pending, Deadline = +24h

    Note over SYS: SLA Countdown Active

    Approver->>SO: Buka SO
    Approver->>SYS: Klik "Review Approval"
    Approver->>SYS: Action = Approve
    SYS->>SO: State = approved
    SYS->>SO: discount_locked = True
    SYS->>SO: Auto action_confirm()
    SO-->>Sales: ✅ SO Confirmed
```

### Skenario 2: Multi-Level Approval (L1 → L2)

```mermaid
sequenceDiagram
    actor Sales as Salesperson
    participant SO as Sales Order
    participant SYS as System
    actor L1 as Supervisor (L1)
    actor L2 as Manager (L2)

    Sales->>SO: SO dengan discount 25%
    Sales->>SO: Confirm
    SO->>SYS: Submit (Level L1)
    SYS->>L1: 📧 Notif Approval

    L1->>SYS: Approve di L1
    SYS->>SYS: required_level = L2
    SYS->>SYS: Advance ke L2
    SYS->>L2: 📧 Notif Approval L2

    L2->>SYS: Approve di L2
    SYS->>SO: Final Approved ✅
    SYS->>SO: Lock + Auto-Confirm
```

### Skenario 3: Counter-Offer

```mermaid
sequenceDiagram
    actor Sales as Salesperson
    participant SO as Sales Order
    participant SYS as System
    actor Approver

    Sales->>SO: Discount 20%
    Sales->>SO: Confirm → Submit
    SYS->>Approver: Notif

    Approver->>SYS: Review Approval
    Approver->>SYS: Counter-Offer: 12%
    SYS->>SO: Proportional reduce all lines
    Note over SO: Line1: 20% → 12%<br/>Line2: 15% → 9%<br/>Line3: 10% → 6%
    SYS->>SO: Approved + Lock + Confirm
```

### Skenario 4: Rejection → Re-submit

```mermaid
sequenceDiagram
    actor Sales as Salesperson
    participant SO as Sales Order
    participant SYS as System
    actor Approver

    Sales->>SO: Discount 30%
    Sales->>SO: Confirm → Submit
    SYS->>Approver: Notif

    Approver->>SYS: Reject (alasan: "Terlalu tinggi")
    SYS->>SO: State = rejected
    SYS->>Sales: 📧 Email Rejection + 🔔 Activity

    Sales->>SO: Revisi discount ke 15%
    Sales->>SO: Klik "Re-submit for Approval"
    SYS->>SO: State = pending (mulai dari L1)
    SYS->>Approver: Notif ulang

    Approver->>SYS: Approve
    SYS->>SO: ✅ Approved + Confirmed
```

### Skenario 5: Delegation + SLA Breach

```mermaid
sequenceDiagram
    actor Sales as Salesperson
    participant SO as Sales Order
    participant SYS as System
    participant CRON as Cron (Hourly)
    actor Approver as Supervisor
    actor Delegate as Wakil
    actor Escalation as Manager

    Sales->>SO: Submit discount 22%
    SYS->>Approver: Notif (deadline +24h)

    Note over Approver: Supervisor sedang cuti

    Approver->>SYS: Delegate ke Wakil
    SYS->>Delegate: 🔔 Activity [DELEGATED]
    SYS->>SYS: Log: delegate action

    Note over SYS: 24 jam berlalu...

    CRON->>SYS: _cron_check_approval_sla()
    SYS->>SYS: Deadline terlewat!
    SYS->>Escalation: ⚠️ SLA BREACH Activity
    SYS->>SYS: Log: escalate action

    Delegate->>SYS: Approve
    SYS->>SO: ✅ Final Approved
```

---

## 5. Cron Jobs

| Cron | Model | Interval | Fungsi |
|------|-------|----------|--------|
| Sale Discount: Check Approval SLA | `sale.order` | 1 jam | Cek `approval_deadline < now`, kirim eskalasi |
| SPK SAW: Daily Product Scoring | `spk.saw.product.score` | 1 hari | Recalculate SAW score semua produk |

---

## 6. Security Matrix

| Model | Manager | Salesman |
|-------|---------|----------|
| `sale.discount.approval.level` | CRUD | R |
| `sale.discount.approval.log` | RWC | RC |
| `sale.discount.approval.wizard` | RWC | - |
| `spk.saw.criterion` | CRUD | R |
| `spk.saw.product.score` | CRUD | R |
| `spk.run.scoring.wizard` | RWC | - |

---

## 7. Mapping KPI → Teknis

| KPI | Sumber Data | Cara Ukur |
|-----|-------------|-----------|
| Approval Cycle Time | `days_pending` | AVG(days_pending) before vs after |
| SLA Compliance | `is_sla_breached`, log `escalate` | COUNT(escalate) / COUNT(submit) |
| Rejection Rate | log `reject` | COUNT(reject) / COUNT(submit) |
| Counter-offer Usage | log `counter_offer` | COUNT(counter_offer) / COUNT(approve) |
| Delegation Rate | log `delegate` | COUNT(delegate) / COUNT(submit) |
| SPK Acceptance Rate | `discount_variance_state = 'aligned'` | COUNT(aligned) / COUNT(with_rec) |

---

## 8. Verifikasi Post-Install Checklist

- [ ] Settings → Sales → Sale Discount Approval → field SLA muncul
- [ ] Sales → Discount Approval → Approval Levels → field SLA, delegate, email visible
- [ ] Sales → SPK Diskon → Kriteria SAW → 4 kriteria default ter-load
- [ ] Sales → SPK Diskon → Hitung Ulang Scoring → jalankan scoring pertama kali
- [ ] Buat SO baru → tambah produk → kolom SPK Rec. Disc. muncul
- [ ] Settings → Technical → Scheduled Actions → 2 cron aktif
- [ ] Test approval flow: submit → approve → auto-confirm + lock
- [ ] Test reject → re-submit flow
- [ ] Test delegate flow
- [ ] Verifikasi email template terkirim (jika mail server configured)

---

*Document Version: 1.0 — Prepared for PT Indopora*
*Odoo Version: 19.0 Community*
