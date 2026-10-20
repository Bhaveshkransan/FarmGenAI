"""add_transport_agent_tables

Revision ID: a1b2c3d4e5f6
Revises: 0b069f7db400
Create Date: 2026-09-26 22:35:00.000000

Creates the full Transport Agent DB schema and patches missing columns
(registration_number, driver_name) on the vehicles table.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '0b069f7db400'
branch_labels = None
depends_on = None


def _table_exists(name):
    from sqlalchemy import inspect
    return name in inspect(op.get_bind()).get_table_names()


def _column_exists(table, col):
    from sqlalchemy import inspect
    return any(c["name"] == col for c in inspect(op.get_bind()).get_columns(table))


def upgrade():
    # vehicles -- create or patch
    if not _table_exists("vehicles"):
        op.create_table(
            "vehicles",
            sa.Column("vehicle_id", sa.String(), primary_key=True),
            sa.Column("transporter_id", sa.String(), nullable=False),
            sa.Column("registration_number", sa.String(), nullable=True),
            sa.Column("driver_name", sa.String(), nullable=True),
            sa.Column("base_rate_per_km", sa.Float(), nullable=True),
            sa.Column("vehicle_type", sa.String(), nullable=False),
            sa.Column("vehicle_name", sa.String(), nullable=True),
            sa.Column("capacity_kg", sa.Float(), nullable=False),
            sa.Column("fuel_type", sa.String(), nullable=False, server_default="Diesel"),
            sa.Column("fuel_efficiency_kmpl", sa.Float(), server_default="10.0"),
            sa.Column("current_location", sa.String(), nullable=True, server_default="Ahmednagar"),
            sa.Column("current_latitude", sa.Float(), nullable=True),
            sa.Column("current_longitude", sa.Float(), nullable=True),
            sa.Column("refrigerated", sa.Boolean(), server_default="false"),
            sa.Column("temperature_min_c", sa.Float(), nullable=True),
            sa.Column("temperature_max_c", sa.Float(), nullable=True),
            sa.Column("status", sa.String(), server_default="AVAILABLE"),
            sa.Column("rating", sa.Float(), server_default="4.5"),
            sa.Column("contact_number", sa.String(), nullable=True),
            sa.Column("owner_contact", sa.String(), nullable=True),
            sa.Column("image_url", sa.String(), nullable=True),
        )
        op.create_index("ix_vehicles_transporter_id", "vehicles", ["transporter_id"])
        op.create_index("ix_vehicles_vehicle_type", "vehicles", ["vehicle_type"])
        op.create_index("ix_vehicles_status", "vehicles", ["status"])
    else:
        for col, col_type in [
            ("registration_number", sa.String()),
            ("driver_name", sa.String()),
            ("base_rate_per_km", sa.Float()),
            ("vehicle_name", sa.String()),
            ("fuel_efficiency_kmpl", sa.Float()),
            ("current_latitude", sa.Float()),
            ("current_longitude", sa.Float()),
            ("temperature_min_c", sa.Float()),
            ("temperature_max_c", sa.Float()),
            ("rating", sa.Float()),
            ("contact_number", sa.String()),
            ("owner_contact", sa.String()),
            ("image_url", sa.String()),
        ]:
            if not _column_exists("vehicles", col):
                op.add_column("vehicles", sa.Column(col, col_type, nullable=True))

    # transport_requests
    if not _table_exists("transport_requests"):
        op.create_table(
            "transport_requests",
            sa.Column("request_id", sa.String(), primary_key=True),
            sa.Column("shipment_id", sa.String(), nullable=True),
            sa.Column("crop", sa.String(), nullable=False),
            sa.Column("quantity_kg", sa.Float(), nullable=False),
            sa.Column("quality", sa.String(), nullable=True, server_default="Grade A"),
            sa.Column("pickup_location", sa.String(), nullable=False),
            sa.Column("delivery_location", sa.String(), nullable=False),
            sa.Column("delivery_deadline_hours", sa.Float(), server_default="12.0"),
            sa.Column("shelf_life_hours", sa.Float(), nullable=True, server_default="24.0"),
            sa.Column("urgency", sa.String(), server_default="NORMAL"),
            sa.Column("temperature_requirement_c", sa.Float(), nullable=True),
            sa.Column("refrigerated_required", sa.Boolean(), server_default="false"),
            sa.Column("status", sa.String(), server_default="PENDING"),
            sa.Column("created_at", sa.String(), nullable=True),
        )

    # fuel_prices
    if not _table_exists("fuel_prices"):
        op.create_table(
            "fuel_prices",
            sa.Column("fuel_price_id", sa.String(), primary_key=True),
            sa.Column("location", sa.String(), nullable=False),
            sa.Column("state", sa.String(), nullable=True, server_default="Maharashtra"),
            sa.Column("fuel_type", sa.String(), nullable=False, server_default="Diesel"),
            sa.Column("price_per_litre", sa.Float(), nullable=False),
            sa.Column("effective_date", sa.String(), nullable=True),
            sa.Column("source", sa.String(), server_default="PPAC/IndianOil Benchmark"),
        )

    # toll_rates
    if not _table_exists("toll_rates"):
        op.create_table(
            "toll_rates",
            sa.Column("toll_id", sa.String(), primary_key=True),
            sa.Column("toll_plaza", sa.String(), nullable=False),
            sa.Column("route_or_highway", sa.String(), nullable=False),
            sa.Column("vehicle_category", sa.String(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("source", sa.String(), server_default="NHAI Rate Matrix"),
        )

    # transport_cost_parameters
    if not _table_exists("transport_cost_parameters"):
        op.create_table(
            "transport_cost_parameters",
            sa.Column("parameter_id", sa.String(), primary_key=True),
            sa.Column("vehicle_type", sa.String(), nullable=False),
            sa.Column("driver_cost_per_hour", sa.Float(), server_default="200.0"),
            sa.Column("maintenance_cost_per_km", sa.Float(), server_default="5.0"),
            sa.Column("loading_cost", sa.Float(), server_default="200.0"),
            sa.Column("unloading_cost", sa.Float(), server_default="200.0"),
            sa.Column("waiting_cost_per_hour", sa.Float(), server_default="150.0"),
            sa.Column("risk_buffer_pct", sa.Float(), server_default="0.05"),
            sa.Column("minimum_profit_margin_pct", sa.Float(), server_default="0.15"),
        )

    # transport_trips
    if not _table_exists("transport_trips"):
        op.create_table(
            "transport_trips",
            sa.Column("trip_id", sa.String(), primary_key=True),
            sa.Column("request_id", sa.String(), nullable=True),
            sa.Column("vehicle_id", sa.String(), nullable=False),
            sa.Column("vehicle_type", sa.String(), nullable=False),
            sa.Column("crop", sa.String(), nullable=True),
            sa.Column("quantity_kg", sa.Float(), nullable=False),
            sa.Column("pickup_location", sa.String(), nullable=False),
            sa.Column("delivery_location", sa.String(), nullable=False),
            sa.Column("distance_km", sa.Float(), nullable=False),
            sa.Column("estimated_duration_hours", sa.Float(), nullable=False),
            sa.Column("fuel_cost", sa.Float(), nullable=False),
            sa.Column("toll_cost", sa.Float(), nullable=False),
            sa.Column("driver_cost", sa.Float(), nullable=False),
            sa.Column("maintenance_cost", sa.Float(), nullable=False),
            sa.Column("loading_cost", sa.Float(), nullable=False),
            sa.Column("waiting_cost", sa.Float(), nullable=False),
            sa.Column("total_operating_cost", sa.Float(), nullable=False),
            sa.Column("minimum_acceptable_price", sa.Float(), nullable=False),
            sa.Column("agreed_price", sa.Float(), nullable=False),
            sa.Column("expected_profit", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), server_default="CONFIRMED"),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=True),
        )


def downgrade():
    for tbl in ["transport_trips", "transport_cost_parameters", "toll_rates", "fuel_prices", "transport_requests"]:
        try:
            op.drop_table(tbl)
        except Exception:
            pass
