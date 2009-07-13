DROP TRIGGER trd
GO
CREATE TRIGGER trd ON mutually_referential_parent
INSTEAD OF DELETE
AS
BEGIN
update mutually_referential_child SET parent_id = NULL WHERE parent_id IN  (SELECT id FROM deleted)
update mutually_referential_parent SET bestchild_id = NULL WHERE id IN  (SELECT id FROM deleted)
END
GO

DROP TRIGGER trd_child
GO
CREATE TRIGGER trd_child ON mutually_referential_child
INSTEAD OF DELETE
AS
BEGIN
update mutually_referential_parent SET bestchild_id = NULL WHERE bestchild_id IN (SELECT id FROM deleted)
update mutually_referential_child SET parent_id = NULL WHERE id IN (SELECT id FROM deleted)
END
GO

DROP TRIGGER trd_after
GO

CREATE TRIGGER trd_after ON mutually_referential_parent
AFTER DELETE
AS
BEGIN
delete FROM mutually_referential_parent WHERE id IN (SELECT id FROM deleted)
END
GO


DROP TRIGGER trd_after_child
GO
 
CREATE TRIGGER trd_after_child ON mutually_referential_child
AFTER DELETE
AS
BEGIN
delete FROM mutually_referential_child WHERE id IN (SELECT id FROM deleted) 
END
GO
