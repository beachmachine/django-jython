DROP TABLE [deferred_serializers_article]
GO
DROP TABLE [deferred_serializers_category]
GO
DROP TABLE [deferred_serializers_author]
GO
DROP TABLE [#deferred_serializers_article]
GO
DROP PROCEDURE [thunk_tmp_deferred_serializers_article]
GO


CREATE TABLE [deferred_serializers_category] (
    [id] int IDENTITY (1, 1) NOT NULL PRIMARY KEY,
    [name] nvarchar(20) NOT NULL
)
GO

CREATE TABLE [deferred_serializers_author] (
    [id] int IDENTITY (1, 1) NOT NULL PRIMARY KEY,
    [name] nvarchar(20) NOT NULL
)
GO

CREATE TABLE [deferred_serializers_article] (
    [id] int IDENTITY (1, 1) NOT NULL PRIMARY KEY,
    [author_id] int NOT NULL REFERENCES [deferred_serializers_author] ([id]),
    [headline] nvarchar(50) NOT NULL,
    [pub_date] datetime NOT NULL
)
GO
-- Seutp the temp table
CREATE TABLE [#deferred_serializers_article] (
	[id] int IDENTITY (1, 1) NOT NULL PRIMARY KEY,
	[author_id] int,
	[headline] nvarchar(50) NOT NULL,
	[pub_date] datetime NOT NULL
)

GO

-- Define a user function that verifies foreign key constraints where foreign keys are not allowed to be NULL
CREATE PROCEDURE [thunk_tmp_deferred_serializers_article] 
AS
BEGIN
        DECLARE @tmp_rowcount int
	DECLARE @rowcount int
	SELECT @tmp_rowcount = COUNT([id]) from [#deferred_serializers_article]

        -- Repeate for each non-null foreign key constraint 
	SELECT @rowcount = COUNT([f].[id]) 
				FROM [deferred_serializers_author] AS f 
				WHERE [f].[id] in 
				(SELECT [author_id] from [#deferred_serializers_article])
        print 'Match rows found: ' + CAST(@rowcount AS VARCHAR)
        print 'Temp rows: ' + CAST(@tmp_rowcount AS VARCHAR)
	IF @rowcount <> @tmp_rowcount
          -- Rowcount has to be non-zero
          RAISERROR ('Foreign key is not satisfied for [deferred_serializers_article].[author_id]',16,1)
        -- To here for each fkey

        -- Finally - move the data from the temp table
        -- Note that we let SQL Server generate new IDs for the records as we shift them back to the 'real' table
        SET IDENTITY_INSERT [deferred_serializers_article] OFF
  	INSERT INTO [deferred_serializers_article] ([author_id], [headline], [pub_date]) 
		(SELECT [author_id], [headline], [pub_date] FROM [#deferred_serializers_article])
        DELETE FROM [#deferred_serializers_article]
        RETURN 1
END

GO



-- Setup fixture data
BEGIN TRANSACTION

	-- Put in a temp record that's a forward reference
	SET IDENTITY_INSERT [#deferred_serializers_article] OFF
	GO
	INSERT INTO [#deferred_serializers_article]
	(author_id, headline, pub_date)
	values
	(4, 'Forward references are ok', '2006-06-01')
	GO
	
	
	-- Put in the reference
	SET IDENTITY_INSERT [deferred_serializers_author] ON
	GO
	INSERT INTO deferred_serializers_author (id, name) VALUES (4, 'Jimmy')
	GO
	SET IDENTITY_INSERT [deferred_serializers_author] OFF
	GO
	
	-- Run the SP to verify references and shift data back
	
	exec thunk_tmp_deferred_serializers_article

COMMIT TRANSACTION
GO
DROP TABLE [#deferred_serializers_article]
GO
SELECT * from [deferred_serializers_article]
GO