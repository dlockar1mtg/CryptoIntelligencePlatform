from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "crypto_platform" / "module22.py"


def main():
    if not TARGET.exists():
        raise FileNotFoundError(f"Missing target: {TARGET}")
    backup = TARGET.with_name("module22_before_v6_0.py")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print(f"Module 22 backup: {backup}")
    text = TARGET.read_text(encoding="utf-8")

    old = '''                    fold_period_rows.append({
                        "run_id": self.run_id,
                        "rebalance_date": date.date(),
                        "next_rebalance_date": next_date.date(),
                        "asset_id": asset,
                        "target_weight": float(item["target_weight"]),
                        "realized_return_pct": realized * 100,
                        "contribution_pct": contribution * 100,
                        "portfolio_period_return_pct": portfolio_return * 100,
                        "btc_period_return_pct": btc_return * 100,
                        "turnover_pct": turnover * 100,
                        "transaction_cost_pct": cost * 100,
                        "calculated_at_utc": utcnow(),
                    })
                fold_returns.append(portfolio_return)'''
    new = '''                    fold_period_rows.append({
                        "run_id": self.run_id,
                        "rebalance_date": date.date(),
                        "next_rebalance_date": next_date.date(),
                        "asset_id": asset,
                        "target_weight": float(item["target_weight"]),
                        "realized_return_pct": realized * 100,
                        "contribution_pct": contribution * 100,
                        "portfolio_period_return_pct": None,
                        "btc_period_return_pct": btc_return * 100,
                        "turnover_pct": turnover * 100,
                        "transaction_cost_pct": cost * 100,
                        "calculated_at_utc": utcnow(),
                    })
                for period_row in fold_period_rows:
                    if (
                        period_row["rebalance_date"] == date.date()
                        and period_row["next_rebalance_date"] == next_date.date()
                    ):
                        period_row["portfolio_period_return_pct"] = (
                            portfolio_return * 100
                        )
                fold_returns.append(portfolio_return)'''
    if old not in text:
        raise RuntimeError("Module 22 partial-return block not found.")
    text = text.replace(old, new, 1)

    old2 = '''        grouped = periods.groupby(
            ["rebalance_date", "next_rebalance_date"], as_index=False
        ).agg(
            portfolio_return_pct=("portfolio_period_return_pct", "max"),
            btc_return_pct=("btc_period_return_pct", "max"),
            turnover_pct=("turnover_pct", "max"),
            transaction_cost_pct=("transaction_cost_pct", "max"),
            cash_weight=("target_weight", lambda x: 0.0),
        )'''
    new2 = '''        grouped = periods.groupby(
            ["rebalance_date", "next_rebalance_date"], as_index=False
        ).agg(
            contribution_sum_pct=("contribution_pct", "sum"),
            btc_return_pct=("btc_period_return_pct", "first"),
            turnover_pct=("turnover_pct", "first"),
            transaction_cost_pct=("transaction_cost_pct", "first"),
        )
        grouped["portfolio_return_pct"] = (
            grouped["contribution_sum_pct"]
            - grouped["transaction_cost_pct"]
        )'''
    if old2 not in text:
        raise RuntimeError("Module 22 summary block not found.")
    text = text.replace(old2, new2, 1)

    old3 = '''        grouped = grouped.merge(cash, on="rebalance_date", how="left")
        pr = grouped["portfolio_return_pct"] / 100'''
    new3 = '''        grouped = grouped.merge(cash, on="rebalance_date", how="left")
        grouped["cash_weight"] = grouped["cash_actual"].fillna(0.0)
        pr = grouped["portfolio_return_pct"] / 100'''
    if old3 not in text:
        raise RuntimeError("Module 22 cash block not found.")
    text = text.replace(old3, new3, 1)

    old4 = '''            future_drawdown = forward_prices.min(axis=1) / btc - 1
            targets = {
                "POSITIVE_RETURN": (future_return > 0).astype(float),
                "DRAWDOWN_20": (future_drawdown <= -0.20).astype(float),
            }'''
    new4 = '''            future_drawdown = forward_prices.min(axis=1) / btc - 1
            full_future_window = forward_prices.notna().all(axis=1)
            positive_target = (future_return > 0).astype(float).where(
                future_return.notna(), float("nan")
            )
            drawdown_target = (future_drawdown <= -0.20).astype(float).where(
                full_future_window, float("nan")
            )
            targets = {
                "POSITIVE_RETURN": positive_target,
                "DRAWDOWN_20": drawdown_target,
            }'''
    if old4 not in text:
        raise RuntimeError("Module 22 label block not found.")
    text = text.replace(old4, new4, 1)

    TARGET.write_text(text, encoding="utf-8")
    print("Module 22 accounting and target alignment patched for v6.0.")


if __name__ == "__main__":
    main()
