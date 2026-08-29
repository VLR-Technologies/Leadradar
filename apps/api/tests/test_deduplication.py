from app.models.business import Business, BusinessAddress, FieldProvenance
from app.services.deduplication import businesses_match, deduplicate_businesses


def business(
    *,
    source: str,
    source_id: str,
    name: str,
    latitude: float,
    longitude: float,
    phone: str | None = None,
    website: str | None = None,
    address: str = "Banjara Hills, Hyderabad",
) -> Business:
    provenance = {}
    if phone:
        provenance["phone"] = (FieldProvenance(phone, source, "medium"),)
    if website:
        provenance["website"] = (FieldProvenance(website, source, "medium"),)
    return Business(
        source_id=source_id,
        source=source,
        name=name,
        category="Dentist",
        address=BusinessAddress(
            formatted=address,
            city="Hyderabad",
            state="Telangana",
            country="India",
        ),
        latitude=latitude,
        longitude=longitude,
        phone=phone,
        email=None,
        website=website,
        opening_hours=None,
        phones=(phone,) if phone else (),
        websites=(website,) if website else (),
        website_status="listed" if website else "not_found",
        sources=(source,),
        source_ids={source: (source_id,)},
        field_provenance=provenance,
    )


def test_cross_source_duplicates_merge_contacts_and_provenance() -> None:
    overture = business(
        source="overture",
        source_id="overture:1",
        name="Smile Care Dental Clinic",
        latitude=17.4140,
        longitude=78.4480,
        phone="+91 98765 43210",
    )
    osm = business(
        source="openstreetmap",
        source_id="node:2",
        name="Smile Care Dental",
        latitude=17.4141,
        longitude=78.4481,
        website="https://smilecare.in",
    )

    leads = deduplicate_businesses([overture, osm])

    assert len(leads) == 1
    assert leads[0].sources == ("overture", "openstreetmap")
    assert leads[0].normalized_phones == ("+919876543210",)
    assert leads[0].website == "https://smilecare.in"
    assert leads[0].field_provenance["phone"][0].source == "overture"
    assert leads[0].field_provenance["website"][0].source == "openstreetmap"


def test_nearby_chain_branches_are_not_merged_when_distance_is_material() -> None:
    first = business(
        source="overture",
        source_id="overture:1",
        name="Apollo Dental",
        latitude=17.4000,
        longitude=78.4000,
        website="https://apollodental.in",
        address="Banjara Hills, Hyderabad",
    )
    second = business(
        source="openstreetmap",
        source_id="node:2",
        name="Apollo Dental",
        latitude=17.4200,
        longitude=78.4200,
        website="https://apollodental.in",
        address="Jubilee Hills, Hyderabad",
    )

    assert not businesses_match(first, second)
    assert len(deduplicate_businesses([first, second])) == 2


def test_close_exact_name_without_contact_data_can_merge() -> None:
    first = business(
        source="overture",
        source_id="overture:1",
        name="ABC Dental Clinic Pvt Ltd",
        latitude=17.40000,
        longitude=78.40000,
    )
    second = business(
        source="openstreetmap",
        source_id="node:2",
        name="ABC Dental Clinic",
        latitude=17.40015,
        longitude=78.40010,
    )

    assert businesses_match(first, second)


def test_deduplication_does_not_transitively_chain_nearby_branches() -> None:
    first = business(
        source="overture",
        source_id="overture:1",
        name="Apollo Dental Clinic Banjara",
        latitude=17.40000,
        longitude=78.40000,
    )
    bridge = business(
        source="openstreetmap",
        source_id="node:2",
        name="Apollo Dental Clinic",
        latitude=17.40035,
        longitude=78.40000,
    )
    second_branch = business(
        source="overture",
        source_id="overture:3",
        name="Apollo Dental Clinic Jubilee",
        latitude=17.40070,
        longitude=78.40000,
    )

    assert businesses_match(first, bridge)
    assert businesses_match(bridge, second_branch)
    assert not businesses_match(first, second_branch)
    assert len(deduplicate_businesses([first, bridge, second_branch])) == 2


def test_deduplication_scales_to_hundreds_without_merging_distinct_branches() -> None:
    businesses = [
        business(
            source="overture",
            source_id=f"overture:{index}",
            name=f"Independent Dental {index}",
            latitude=17.0 + index * 0.004,
            longitude=78.0,
            address=f"Branch {index}, Hyderabad",
        )
        for index in range(600)
    ]

    assert len(deduplicate_businesses(businesses)) == 600
