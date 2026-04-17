from typing import Dict
from pyiceberg.catalog import Catalog
from pyiceberg.schema import Schema
from pyiceberg.table import Table
from pyiceberg.types import (
    NestedField,
    StringType,
    LongType,
    DoubleType,
    MapType,
    BooleanType,
    ListType
)
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import IdentityTransform, BucketTransform
from pyiceberg.table.sorting import (
    SortOrder, SortField, SortDirection, NullOrder
)
from utils import create_table, load_s3_tables_catalog

# CREATE TABLE genomic_variants (
#   sample_id UUID NOT NULL,
#   chrom STRING NOT NULL,
#   pos BIGINT NOT NULL,
#   ref STRING NOT NULL,
#   alt STRING NOT NULL,
#   qual DOUBLE,
#   filter STRING,
#   genotype STRING,
#   info MAP<STRING, STRING>,
#   attributes MAP<STRING, STRING>,
#   is_reference_block BOOLEAN,
# )
genomic_variants_schema: Schema = Schema(
    NestedField(1, "sample_name", StringType(), required=True),
    NestedField(2, "variant_name", StringType(), required=True,
                doc="The ID field in VCF files, '.' indicates no name"),
    NestedField(3, "chrom", StringType(), required=True),
    NestedField(4, "pos", LongType(), required=True),
    NestedField(5, "ref", StringType(), required=True),
    NestedField(6, "alt", ListType(element_id=1000,
                                   element_type=StringType(),
                                   element_required=True),
                required=True),
    NestedField(7, "qual", DoubleType()),
    NestedField(8, "filter", StringType()),
    NestedField(9, "genotype", StringType()),
    NestedField(10, "info", MapType(key_type=StringType(),
                                    key_id=1001,
                                    value_type=StringType(),
                                    value_id=1002,
                                    required=False)),
    NestedField(11, "attributes", MapType(key_type=StringType(),
                                          key_id=2001,
                                          value_type=StringType(),
                                          value_id=2002,
                                          required=False)),
    NestedField(12, "is_reference_block", BooleanType(),
                doc='Used in GVCF for non-variant sites'),
    identifier_field_ids=[1, 2, 3, 4]      # defines the 'primary key' for upserts
)

genomic_variants_partition_spec: PartitionSpec = PartitionSpec(
    PartitionField(source_id=1,
                   field_id=1001,
                   transform=IdentityTransform(),
                   name="sample_bucket"),
    PartitionField(source_id=3,
                   field_id=1002,
                   transform=IdentityTransform(),
                   name="chrom")
)
genomic_variants_sort_order: SortOrder = SortOrder(
    # sort by chrom, and pos
    SortField(source_id=3,
              transform=IdentityTransform(),
              direction=SortDirection.ASC,
              null_order=NullOrder.NULLS_LAST),
    SortField(source_id=4,
              transform=IdentityTransform(),
              direction=SortDirection.ASC,
              null_order=NullOrder.NULLS_LAST),
)


def create_schema_tables(catalog: Catalog, namespace: str) -> Dict[str, Table]:
    table_name_genomic_variants: str = "genomic_variants_fixed"

    print(f"Creating tables in namespace {namespace} ...")
    print(f"Creating {table_name_genomic_variants}")
    genomic_variants: Table = create_table(
        catalog=catalog,
        namespace=namespace,
        table_name=table_name_genomic_variants,
        schema=genomic_variants_schema,
        partition_spec=genomic_variants_partition_spec,
        sort_order=genomic_variants_sort_order)
    print(f"Created {genomic_variants}")

    return {
        table_name_genomic_variants: genomic_variants
    }


def main():
    import argparse
    from utils import create_namespace

    parser = argparse.ArgumentParser(description='Create Iceberg table for genomic variant data (Schema 3)')
    parser.add_argument('--bucket-arn', required=True, help='S3Tables bucket ARN')
    args = parser.parse_args()

    print("Connecting to catalog ...")
    catalog = load_s3_tables_catalog(args.bucket_arn)
    print("Connected to catalog")

    print("Creating namespace ...")
    namespace: str = "variant_db_3"
    create_namespace(catalog, namespace)
    print("Namespace created")

    print("Creating tables ...")
    create_schema_tables(catalog, namespace)
    print("Tables created")
    print("Done")


if __name__ == "__main__":
    main()
