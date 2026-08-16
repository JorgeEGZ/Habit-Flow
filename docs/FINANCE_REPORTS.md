# Finance Reports

HabitFlow finance reports are authenticated, read-only views over real user-owned transactions. They do not include recurring projections. A manually registered recurring occurrence is included because it creates a real transaction.

## Month Handling

Every report endpoint accepts an optional `month` query parameter in strict `YYYY-MM` format. When omitted, the backend resolves the current month from `APP_TIMEZONE`, which defaults to `America/Bogota`. Future months are valid and return complete zero-value report structures when they have no transactions.

Months and period dates are date-only values. Frontend callers keep them as raw strings and must not parse them through JavaScript `Date` or derive them with `toISOString()`.

The selected month is the current period. The previous period is the preceding calendar month, including the December-to-January boundary. All transaction period boundaries are inclusive.

## Endpoints

### `GET /api/v1/finances/reports/monthly?month=YYYY-MM`

Returns the selected month, previous month, transaction summaries, comparisons, spending by category, monthly budgets, and deterministic insights.

`current.total_expenses` includes every real expense transaction. `monthly_budgets.total_spent_amount` includes only expense categories that have a budget. Recurring projections never contribute to either value.

Comparison percentage changes are rounded to two decimal places with `ROUND_HALF_UP`. A percentage is `null` when the previous amount is zero. Comparisons use the absolute previous amount as the denominator so negative previous net values remain meaningful.

### `GET /api/v1/finances/reports/monthly-trends?month=YYYY-MM`

Returns exactly six chronological calendar months ending at the selected month. Empty months remain in the response with zero totals. `savings_rate` is `net / total_income * 100`, rounded to two decimal places with `ROUND_HALF_UP`, and is `null` when total income is zero.

### `GET /api/v1/finances/reports/monthly.xlsx?month=YYYY-MM`

Returns an XLSX attachment named `habitflow-monthly-report-YYYY-MM.xlsx`. It reuses the monthly report and monthly trend service logic with one captured app-local date. The export is read-only and contains no raw transactions or recurring projections.

## Monthly Insights

The monthly report response contains an additive `insights` array. Each item has a stable `code`, a `tone`, and a flexible `values` object. The exact keys in `values` are determined by `code`; consumers must not infer financial aggregates beyond the values provided.

| Code | Tone | Values keys |
| --- | --- | --- |
| `no_activity` | `info` | none |
| `budget_exceeded` | `danger` | `count`, `total_over_budget_amount` |
| `budget_limit_reached` | `warning` | `count`, `highest_usage_percentage`, `category_name` |
| `budget_near_limit` | `warning` | `count`, `highest_usage_percentage`, `category_name` |
| `no_income` | `warning` | none |
| `negative_net` | `danger` | `net`, `shortfall_amount` |
| `break_even` | `neutral` | none |
| `positive_savings_rate` | `success` | `net`, `savings_rate` |
| `expenses_increased` | `warning` | `current_amount`, `previous_amount`, `absolute_change`, `percentage_change` |
| `expenses_decreased` | `success` | `current_amount`, `previous_amount`, `absolute_change`, `percentage_change` |
| `expenses_no_comparison` | `info` | `current_amount`, `previous_amount`, `absolute_change`, `percentage_change` |
| `top_spending_category` | `info` | `category_id`, `category_name`, `amount`, `share_percentage` |

The backend emits at most four insights in this deterministic priority order:

1. Budget status.
2. Net or income status.
3. Expense comparison.
4. Top spending category.

When the current month has no transactions, `no_activity` is the only insight.

## XLSX Workbook Contract

The workbook contains exactly four worksheets in this order:

1. `Summary`
2. `Spending by Category`
3. `Budgets`
4. `Six-Month Trends`

There is no `Insights` worksheet.

| Worksheet | Headers |
| --- | --- |
| Summary | `month`, `period_start`, `period_end`, `total_income`, `total_expenses`, `net`, `transaction_count`, `income_transaction_count`, `expense_transaction_count`, `previous_month`, `previous_period_start`, `previous_period_end`, `previous_total_income`, `previous_total_expenses`, `previous_net`, `previous_transaction_count`, `income_absolute_change`, `income_percentage_change`, `expenses_absolute_change`, `expenses_percentage_change`, `net_absolute_change`, `net_percentage_change` |
| Spending by Category | `month`, `category_name`, `amount`, `transaction_count`, `share_percentage`, `category_id` |
| Budgets | `month`, `category_name`, `budget_amount`, `spent_amount`, `remaining_amount`, `over_budget_amount`, `transaction_count`, `usage_percentage`, `exceeded`, `budget_id`, `category_id` |
| Six-Month Trends | `month`, `period_start`, `period_end`, `total_income`, `total_expenses`, `net`, `transaction_count`, `income_transaction_count`, `expense_transaction_count`, `savings_rate` |

Amounts are raw integer COP values. Percentages are numeric percentage points with two-decimal formatting. Dates are ISO strings. Empty datasets still produce valid header rows.

The XLSX utility removes NUL characters from text and prefixes an apostrophe when the first non-whitespace character is `=`, `+`, `-`, or `@`. It does not write Excel formulas.

## Frontend Request Coordination

The finance store uses independent monotonic request identifiers for the monthly report and monthly trends. Only the latest request may update data, loading state, or error state.

The reports composable adds page-level coordination:

1. On first entry it requests the monthly report without `month`.
2. It adopts `report.month` as the canonical selected month.
3. It requests trends using that exact month.
4. On later changes it sends the selected raw `YYYY-MM` value to both resources.
5. A stale report response cannot replace the selected month or trigger a trends request.

Report and trend loading and errors remain independent. An XLSX export error is local to the reports workspace and is cleared when the selected month changes.
