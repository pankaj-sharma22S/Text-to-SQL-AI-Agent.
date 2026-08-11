from pydantic import BaseModel, Field

class ColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    default: str | None = None

class ForeignKeyInfo(BaseModel):
    column: str
    referenced_table: str
    referenced_column: str

class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]
    primary_keys: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = Field(default_factory=list)

class DatabaseSchema(BaseModel):
    tables: list[TableInfo]

    def to_prompt(self) -> str:
        lines = []
        for table in self.tables:
            lines.append(f"TABLE: {table.name}")
            for column in table.columns:
                null = "NULL" if column.nullable else "NOT NULL"
                lines.append(f"  - {column.name}: {column.data_type} {null}")
            if table.primary_keys:
                lines.append(f"  PRIMARY KEY: {', '.join(table.primary_keys)}")
            for fk in table.foreign_keys:
                lines.append(f"  FOREIGN KEY: {fk.column} -> {fk.referenced_table}.{fk.referenced_column}")
            lines.append("")
        return "\n".join(lines)
