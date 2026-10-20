"""
tests/test_live_postgresql_transport_runtime.py
--------------------------------------------------------------------
FarmGenAI / AgriNegotiator — LIVE POSTGRESQL RUNTIME & CONCURRENCY CERTIFICATION
--------------------------------------------------------------------

Validates against the live PostgreSQL 16 instance on port 5433:
1. Live Database Connectivity & Schema Initialisation:
   - Verifies tables: transport_providers, vehicles, transport_carrier_bookings, transport_negotiations.
2. Authoritative Persistence Across Connections:
   - INSERT -> COMMIT -> CLOSE CONNECTION -> NEW ENGINE / CONNECTION -> SELECT.
3. Concurrent Vehicle Reservation Race Condition:
   - Two concurrent buyers attempting to reserve the exact same vehicle simultaneously.
   - Proves row-locking guarantees exactly ONE succeeds and ONE fails cleanly with VehicleAlreadyBookedException.
4. Distributed Idempotency:
   - Duplicate booking requests for same negotiation_id return existing booking without double-booking.
5. Transactional Rollback Safety:
   - Aborted booking cleanly rolls back without orphaned entities or corrupted vehicle status.
"""

import sys, os, uuid, asyncio, pytest
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from backend.core.config import settings
from backend.db.session import Base
from backend.db.models.transport_agent_models import (
    DBTransportProvider, DBVehicle, DBTransportNegotiation, DBTransportBooking
)
from backend.db.models.schema import DBBooking
from backend.services.transporter_marketplace_service import reserve_vehicle_and_create_booking_async
from backend.core.exceptions import VehicleAlreadyBookedException, ConflictException

from sqlalchemy.pool import NullPool

# Target the live PostgreSQL database directly
LIVE_PG_URL = settings.DATABASE_URL
if "postgres" not in LIVE_PG_URL.lower():
    LIVE_PG_URL = "postgresql+asyncpg://admin:admin_password@localhost:5433/agrinegotiator"


@pytest.fixture
async def pg_engine():
    """Create isolated async engine for live PostgreSQL testing with NullPool."""
    engine = create_async_engine(LIVE_PG_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE transport_carrier_bookings ADD COLUMN IF NOT EXISTS negotiation_id VARCHAR;"))
            await conn.execute(text("ALTER TABLE transport_carrier_bookings ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR;"))
        except Exception:
            pass
    yield engine
    await engine.dispose()


@pytest.fixture
async def pg_session(pg_engine):
    """Provide clean session per test."""
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


# ==============================================================================
# 1. LIVE POSTGRES CONNECTIVITY & SCHEMA VERIFICATION
# ==============================================================================
@pytest.mark.asyncio
async def test_01_live_postgres_connectivity_and_schema_initialization(pg_session):
    """
    Empirically verifies connectivity and authoritative schema in live PostgreSQL 16.
    """
    res = await pg_session.execute(text("SELECT version();"))
    version_str = res.scalar()
    assert "PostgreSQL" in version_str, f"Expected PostgreSQL, got {version_str}"
    print(f"\n[LIVE PG] Connected to: {version_str}")

    # Verify tables in public schema
    stmt = text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    tables = [row[0] for row in (await pg_session.execute(stmt)).fetchall()]
    print(f"[LIVE PG] Tables present: {tables}")

    required_tables = [
        "transport_providers",
        "vehicles",
        "transport_carrier_bookings",
        "transport_negotiations"
    ]
    for table in required_tables:
        assert table in tables, f"Required table '{table}' must exist in live PostgreSQL!"


# ==============================================================================
# 2. PERSISTENCE ACROSS RECONNECT (INSERT -> COMMIT -> NEW CONN -> SELECT)
# ==============================================================================
@pytest.mark.asyncio
async def test_02_live_postgres_authoritative_persistence_across_connections(pg_engine):
    """
    Proves true persistence across independent connections:
    Connection 1: Inserts Provider, Vehicle, Negotiation, Booking and Commits.
    Connection 2: Brand new engine connection queries and verifies persisted state.
    """
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)
    
    unique_suffix = uuid.uuid4().hex[:6]
    provider_id = f"prov_pg_{unique_suffix}"
    vehicle_id = f"veh_pg_{unique_suffix}"
    neg_id = f"neg_pg_{unique_suffix}"
    booking_id = f"booking_pg_{unique_suffix}"

    # Connection 1: INSERT & COMMIT
    async with session_factory() as session1:
        provider = DBTransportProvider(
            provider_id=provider_id,
            name="Maharashtra Express Logistics Ltd",
            service_area="Nashik-Pune-Mumbai",
            rating=4.8,
            reliability=0.96,
            completion_rate=0.99,
            status="ACTIVE"
        )
        vehicle = DBVehicle(
            vehicle_id=vehicle_id,
            transporter_id=provider_id,
            vehicle_name="Eicher Pro 2049",
            vehicle_type="LCV",
            capacity_kg=3500.0,
            base_rate_per_km=24.0,
            status="AVAILABLE",
            fuel_efficiency_kmpl=9.5
        )
        negotiation = DBTransportNegotiation(
            negotiation_id=neg_id,
            request_id=f"req_{unique_suffix}",
            provider_id=provider_id,
            vehicle_id=vehicle_id,
            round_num=1,
            offer=4500.0,
            counter_offer=4200.0,
            transport_floor=3800.0,
            status="ACCEPTED"
        )
        booking = DBTransportBooking(
            booking_id=booking_id,
            request_id=f"req_{unique_suffix}",
            negotiation_id=neg_id,
            provider_id=provider_id,
            vehicle_id=vehicle_id,
            agreed_freight=4200.0,
            transport_floor=3800.0,
            farmer_net_realization=27.20,
            farmer_floor=25.0,
            status="CONFIRMED"
        )
        session1.add_all([provider, vehicle, negotiation, booking])
        await session1.commit()

    # Connection 2: NEW CONNECTION -> SELECT & VERIFY
    new_engine = create_async_engine(LIVE_PG_URL, echo=False)
    new_factory = async_sessionmaker(new_engine, expire_on_commit=False, class_=AsyncSession)

    async with new_factory() as session2:
        prov_db = (await session2.execute(select(DBTransportProvider).where(DBTransportProvider.provider_id == provider_id))).scalars().first()
        veh_db = (await session2.execute(select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id))).scalars().first()
        neg_db = (await session2.execute(select(DBTransportNegotiation).where(DBTransportNegotiation.negotiation_id == neg_id))).scalars().first()
        book_db = (await session2.execute(select(DBTransportBooking).where(DBTransportBooking.booking_id == booking_id))).scalars().first()

        assert prov_db is not None, "Provider must be persisted in PostgreSQL"
        assert veh_db is not None, "Vehicle must be persisted in PostgreSQL"
        assert neg_db is not None, "Negotiation must be persisted in PostgreSQL"
        assert book_db is not None, "Booking must be persisted in PostgreSQL"

        assert prov_db.name == "Maharashtra Express Logistics Ltd"
        assert veh_db.capacity_kg == 3500.0
        assert neg_db.counter_offer == 4200.0
        assert book_db.agreed_freight == 4200.0
        assert book_db.farmer_net_realization == 27.20

    await new_engine.dispose()
    print("\n[PASS] Gate: Authoritative persistence verified across independent PostgreSQL connections.")


# ==============================================================================
# 3. CONCURRENT VEHICLE RESERVATION RACE CONDITION (ROW LOCKING)
# ==============================================================================
@pytest.mark.asyncio
async def test_03_concurrent_vehicle_reservation_race_condition(pg_engine):
    """
    Mandatory Production Concurrency Certification:
    Simulates Buyer A and Buyer B simultaneously attempting to book the SAME vehicle.
    Guarantees:
    - Only ONE booking transaction succeeds.
    - The losing transaction receives VehicleAlreadyBookedException.
    - Exactly 1 booking record is persisted in PostgreSQL.
    - Vehicle status is transitionally updated to 'BOOKED'.
    """
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)
    unique_veh_id = f"veh_race_{uuid.uuid4().hex[:6]}"
    provider_id = f"prov_race_{uuid.uuid4().hex[:6]}"

    # Step 1: Insert an Available Vehicle in PostgreSQL
    async with session_factory() as session:
        provider = DBTransportProvider(provider_id=provider_id, name="Fleet Concurrency Test Co")
        vehicle = DBVehicle(
            vehicle_id=unique_veh_id,
            transporter_id=provider_id,
            vehicle_type="Medium Truck",
            capacity_kg=5000.0,
            status="AVAILABLE"
        )
        session.add_all([provider, vehicle])
        await session.commit()

    # Step 2: Define Worker A and Worker B booking requests
    payload_a = {
        "booking_id": f"book_a_{uuid.uuid4().hex[:6]}",
        "negotiation_id": f"neg_a_{uuid.uuid4().hex[:6]}",
        "provider_id": provider_id,
        "vehicle_id": unique_veh_id,
        "agreed_freight": 6200.0,
        "transport_floor": 5500.0,
        "farmer_net_realization": 26.50,
        "farmer_floor": 24.0,
        "booked_by": "buyer_enterprise_alpha"
    }

    payload_b = {
        "booking_id": f"book_b_{uuid.uuid4().hex[:6]}",
        "negotiation_id": f"neg_b_{uuid.uuid4().hex[:6]}",
        "provider_id": provider_id,
        "vehicle_id": unique_veh_id,
        "agreed_freight": 6500.0,
        "transport_floor": 5500.0,
        "farmer_net_realization": 27.00,
        "farmer_floor": 24.0,
        "booked_by": "buyer_retail_beta"
    }

    async def worker_attempt(payload: Dict[str, Any]) -> Dict[str, Any]:
        async with session_factory() as sess:
            return await reserve_vehicle_and_create_booking_async(payload, session=sess)

    # Step 3: Run Worker A and Worker B concurrently
    results = await asyncio.gather(
        worker_attempt(payload_a),
        worker_attempt(payload_b),
        return_exceptions=True
    )

    successes = [r for r in results if isinstance(r, dict) and r.get("success") is True]
    failures = [r for r in results if isinstance(r, (VehicleAlreadyBookedException, ConflictException))]

    print(f"\n[RACE CONDITION RESULTS] Successes: {len(successes)} | Failures: {len(failures)}")
    assert len(successes) == 1, f"Exactly ONE concurrent reservation must succeed! Got {len(successes)}"
    assert len(failures) == 1, f"Exactly ONE concurrent reservation must fail with conflict! Got {len(failures)}"

    # Step 4: Verify PostgreSQL Database State
    async with session_factory() as session:
        veh_db = (await session.execute(select(DBVehicle).where(DBVehicle.vehicle_id == unique_veh_id))).scalars().first()
        bookings_db = (await session.execute(select(DBTransportBooking).where(DBTransportBooking.vehicle_id == unique_veh_id))).scalars().all()

        assert veh_db.status == "BOOKED", "Vehicle status must be updated to 'BOOKED'"
        assert len(bookings_db) == 1, f"PostgreSQL must contain exactly 1 booking for this vehicle! Found {len(bookings_db)}"
        print(f"[PASS] Winner Booking ID: {bookings_db[0].booking_id} by {bookings_db[0].provider_id}")


# ==============================================================================
# 4. DISTRIBUTED IDEMPOTENCY ACROSS RETRIES
# ==============================================================================
@pytest.mark.asyncio
async def test_04_distributed_api_idempotency(pg_engine):
    """
    Verifies that a duplicate client request (same negotiation_id or idempotency_key)
    returns the existing booking without creating duplicate bookings in PostgreSQL.
    """
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)
    unique_veh = f"veh_idem_{uuid.uuid4().hex[:6]}"
    unique_neg = f"neg_idem_{uuid.uuid4().hex[:6]}"
    unique_key = f"idem_key_{uuid.uuid4().hex[:6]}"

    # Setup vehicle
    async with session_factory() as session:
        v = DBVehicle(vehicle_id=unique_veh, transporter_id="prov_idem", vehicle_type="Mini Truck", capacity_kg=1500.0, status="AVAILABLE")
        session.add(v)
        await session.commit()

    payload = {
        "booking_id": f"book_{uuid.uuid4().hex[:6]}",
        "negotiation_id": unique_neg,
        "idempotency_key": unique_key,
        "vehicle_id": unique_veh,
        "agreed_freight": 3200.0,
        "transport_floor": 2800.0,
        "farmer_net_realization": 28.0
    }

    # Attempt 1: First booking
    async with session_factory() as sess1:
        res1 = await reserve_vehicle_and_create_booking_async(payload, session=sess1)
    assert res1["success"] is True
    assert res1["is_idempotent_replay"] is False
    original_booking_id = res1["booking_id"]

    # Attempt 2: Network retry with identical payload
    async with session_factory() as sess2:
        res2 = await reserve_vehicle_and_create_booking_async(payload, session=sess2)
    assert res2["success"] is True
    assert res2["is_idempotent_replay"] is True
    assert res2["booking_id"] == original_booking_id

    # Verify PostgreSQL count is strictly 1
    async with session_factory() as session:
        records = (await session.execute(
            select(DBTransportBooking).where(DBTransportBooking.negotiation_id == unique_neg)
        )).scalars().all()
        assert len(records) == 1, f"Expected exactly 1 booking record, found {len(records)}"

    print("\n[PASS] Gate: Distributed idempotency verified. Retries return existing booking without duplicates.")


# ==============================================================================
# 5. TRANSACTIONAL ROLLBACK SAFETY
# ==============================================================================
@pytest.mark.asyncio
async def test_05_transactional_rollback_on_failure(pg_engine):
    """
    Proves that a runtime error during the booking sequence cleanly rolls back,
    leaving vehicle status intact and creating zero orphaned records.
    """
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)
    unique_veh = f"veh_roll_{uuid.uuid4().hex[:6]}"

    async with session_factory() as session:
        v = DBVehicle(vehicle_id=unique_veh, transporter_id="prov_roll", vehicle_type="LCV", capacity_kg=2500.0, status="AVAILABLE")
        session.add(v)
        await session.commit()

    # Attempt booking that triggers simulated error
    async with session_factory() as session:
        try:
            # Row lock vehicle
            veh = (await session.execute(select(DBVehicle).where(DBVehicle.vehicle_id == unique_veh).with_for_update())).scalars().first()
            veh.status = "BOOKED"
            # Intentionally insert invalid object to trigger DB error
            session.add(DBTransportBooking(
                booking_id=f"book_err_{uuid.uuid4().hex[:6]}",
                provider_id="prov_roll",
                vehicle_id=unique_veh,
                agreed_freight=None  # NOT NULL violation
            ))
            await session.commit()
        except Exception:
            await session.rollback()

    # Verify vehicle remains AVAILABLE and no booking was created
    async with session_factory() as session:
        veh_check = (await session.execute(select(DBVehicle).where(DBVehicle.vehicle_id == unique_veh))).scalars().first()
        book_check = (await session.execute(select(DBTransportBooking).where(DBTransportBooking.vehicle_id == unique_veh))).scalars().all()

        assert veh_check.status == "AVAILABLE", "Vehicle must remain AVAILABLE after transaction rollback!"
        assert len(book_check) == 0, "No orphaned booking records should exist after rollback!"

    print("\n[PASS] Gate: Transactional rollback safety verified. Database integrity preserved.")
