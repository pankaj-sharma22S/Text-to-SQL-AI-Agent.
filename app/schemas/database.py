from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool = True


class ForeignKeyInfo(BaseModel):
    column: str
    referenced_table: str
    referenced_column: str


class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]
    primary_keys: list[str] = []
    foreign_keys: list[ForeignKeyInfo] = []


class DatabaseSchema(BaseModel):
    tables: list[TableInfo]

    def to_prompt(self) -> str:
        """Convert database schema into LLM-friendly text."""
        output = []

        for table in self.tables:
            output.append(f"TABLE: {table.name}")

            for column in table.columns:
                nullable = "NULL" if column.nullable else "NOT NULL"
                output.append(
                    f"  - {column.name}: "
                    f"{column.data_type} {nullable}"
                )

            if table.primary_keys:
                output.append(
                    f"  PRIMARY KEY: {', '.join(table.primary_keys)}"
                )

            for fk in table.foreign_keys:
                output.append(
                    f"  FOREIGN KEY: {fk.column} "
                    f"→ {fk.referenced_table}.{fk.referenced_column}"
                )

            output.append("")

        return "\n".join(output)