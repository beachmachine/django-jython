

--- Postgresql

BEGIN;
CREATE TABLE "mutually_referential_parent" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL,
    "bestchild_id" integer NULL
)
;
CREATE TABLE "mutually_referential_child" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL,
    "parent_id" integer NOT NULL REFERENCES "mutually_referential_parent" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
ALTER TABLE "mutually_referential_parent" ADD CONSTRAINT bestchild_id_refs_id_7ce81e28 FOREIGN KEY ("bestchild_id") REFERENCES "mutually_referential_child" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "mutually_referential_parent_bestchild_id" ON "mutually_referential_parent" ("bestchild_id");
CREATE INDEX "mutually_referential_child_parent_id" ON "mutually_referential_child" ("parent_id");
COMMIT;
-- Notes: Postgresql lets you specify DEFERRABLE constraints so this allows us
-- to mangle relationships up without having to worry until transaction commit
-- time.

--- SQLite3
BEGIN;
CREATE TABLE "mutually_referential_parent" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL,
    "bestchild_id" integer NULL
)
;
CREATE TABLE "mutually_referential_child" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL,
    "parent_id" integer NOT NULL REFERENCES "mutually_referential_parent" ("id")
)
;
CREATE INDEX "mutually_referential_parent_bestchild_id" ON "mutually_referential_parent" ("bestchild_id");
CREATE INDEX "mutually_referential_child_parent_id" ON "mutually_referential_child" ("parent_id");
COMMIT;
--- Notes: SQLite doesn't support adding/removing constraints so we don't see  the "bestchild" constraint here.

-- SQL Server 2000

BEGIN;
CREATE TABLE [mutually_referential_parent] (
    [id] int IDENTITY (1, 1) NOT NULL PRIMARY KEY,
    [name] nvarchar(100) NOT NULL,
    [bestchild_id] int NULL
)
;
CREATE TABLE [mutually_referential_child] (
    [id] int IDENTITY (1, 1) NOT NULL PRIMARY KEY,
    [name] nvarchar(100) NOT NULL,
    [parent_id] int NOT NULL REFERENCES [mutually_referential_parent] ([id])
)
;
ALTER TABLE [mutually_referential_parent] ADD CONSTRAINT [bestchild_id_refs_id_4a696c71] FOREIGN KEY ([bestchild_id]) REFERENCES [mutually_referential_child] ([id]);
CREATE INDEX [mutually_referential_parent_bestchild_id] ON [mutually_referential_parent] ([bestchild_id]);
CREATE INDEX [mutually_referential_child_parent_id] ON [mutually_referential_child] ([parent_id]);
DROP TRIGGER trd;
CREATE TRIGGER trd ON mutually_referential_parent
INSTEAD OF DELETE
AS
BEGIN
update mutually_referential_child SET parent_id = NULL WHERE parent_id IN  (SELECT id FROM deleted)
update mutually_referential_parent SET bestchild_id = NULL WHERE id IN  (SELECT id FROM deleted)
END;
DROP TRIGGER trd_child;
CREATE TRIGGER trd_child ON mutually_referential_child
INSTEAD OF DELETE
AS
BEGIN
update mutually_referential_parent SET bestchild_id = NULL WHERE bestchild_id IN (SELECT id FROM deleted)
update mutually_referential_child SET parent_id = NULL WHERE id IN (SELECT id FROM deleted)
END;
DROP TRIGGER trd_after;
CREATE TRIGGER trd_after ON mutually_referential_parent
AFTER DELETE
AS
BEGIN
delete FROM mutually_referential_parent WHERE id IN (SELECT id FROM deleted)
END;
DROP TRIGGER trd_after_child;
CREATE TRIGGER trd_after_child ON mutually_referential_child
AFTER DELETE
AS
BEGIN
delete FROM mutually_referential_child WHERE id IN (SELECT id FROM deleted) 
END;
COMMIT;

