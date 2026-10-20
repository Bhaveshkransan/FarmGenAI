import sys
path = '/app/alembic/versions/d64404dd3c42_auto_fix_missing_columns.py'
try:
    with open(path, 'r') as f:
        c = f.read()

    c = c.replace("op.add_column('produce', sa.Column('workflow_mode', sa.String(), nullable=False))", 
                  "op.add_column('produce', sa.Column('workflow_mode', sa.String(), server_default='manual', nullable=False))")

    c = c.replace("existing_type=postgresql.JSON(astext_type=sa.Text()),\n               nullable=False", 
                  "existing_type=postgresql.JSON(astext_type=sa.Text()),\n               nullable=True")

    with open(path, 'w') as f:
        f.write(c)
    print("Patch applied successfully.")
except Exception as e:
    print(f"Migration patch script skipped: {e}")
