'''
We define a custom command to install the stored procedures into MSSQL2K
'''
from django.core.management.base import NoArgsCommand
from django.core.management.color import no_style
from optparse import make_option
import sys

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list 

    help = "Install the stored procedures required to make SQL Server 2000 play nice"

    def handle_noargs(self, **options):
        from django.db import connection, transaction, models
        from django.conf import settings
        from django.core.management.sql import custom_sql_for_model, emit_post_sync_signal

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive')
        show_traceback = options.get('traceback', False)

        self.style = no_style()

        cursor = connection.cursor()

        print "SQL Server 2000: Installing pagination stored procedure"
        cursor.execute(RETURN_PAGE_SQL)
        print "SQL Server 2000: Installing regular expression support" 
        cursor.execute(REGEX_FUNC)

        transaction.commit_unless_managed()



RETURN_PAGE_SQL = '''
CREATE PROCEDURE ReturnPage @query varchar(2000), @OrderBy varchar(2000),
                            @StartRow int, @EndRow int
AS
BEGIN
declare @ColList varchar(2000);
declare @Where varchar(2000);
declare @i int; 
declare @i2 int;
declare @tmp varchar(2000);
declare @dec varchar(2000);
declare @f varchar(100);
declare @d varchar(100);
declare @Symbol char(2);
declare @SQL varchar(5000);
declare @Sort varchar(2000);
set @Sort = @OrderBy + ', '
set @dec = ''
set @Where  = ''
set @SQL = ''
set @i = charindex(',' , @Sort)
while @i != 0
 begin
  set @tmp = left(@Sort,@i-1)
  set @i2 = charindex(' ', @tmp)
  set @f = ltrim(rtrim(left(@tmp,@i2-1)))
  set @d = ltrim(rtrim(substring(@tmp,@i2+1,100)))
  set @Sort = rtrim(ltrim(substring(@Sort,@i+1,100)))
  set @i = charindex(',', @Sort)
  set @symbol = case when @d = 'ASC' then '>' else '<' end +
                case when @i=0 then '=' else '' end
  set @dec = @dec + 'declare @' + @f + ' sql_variant; '
  set @ColList = isnull(replace(replace(@colList,'>','='),'<','=') + ' and ','') +
                 @f + @Symbol + ' @' + @f
  set @Where = @Where + ' OR (' + @ColList + ') '
  set @SQL = @SQL + ', @' + @f + '= ' + @f
 end
set @SQL = @dec + ' ' +
           'SET ROWCOUNT ' + convert(varchar(10), @StartRow) + '; ' +
           'SELECT ' + substring(@SQL,3,7000) + ' from (' + @query + ') a ORDER BY ' +
           @OrderBy + '; ' + 'SET ROWCOUNT ' +
           convert(varchar(10), 1 + @EndRow - @StartRow) + '; ' +
           'select * from (' + @query + ') a WHERE ' +
           substring(@Where,4,7000) + ' ORDER BY ' + @OrderBy + '; SET ROWCOUNT 0;'
exec(@SQL)
END
'''

REGEX_FUNC = '''
CREATE FUNCTION dbo.regex
	(
		@source varchar(5000),
		@regexp varchar(1000),
		@ignorecase bit = 0
	)
RETURNS bit
AS
	BEGIN
		DECLARE @hr integer
		DECLARE @objRegExp integer
		DECLARE @objMatches integer
		DECLARE @objMatch integer
		DECLARE @count integer
		DECLARE @results bit
		
		EXEC @hr = sp_OACreate 'VBScript.RegExp', @objRegExp OUTPUT
		IF @hr <> 0 BEGIN
			SET @results = 0
			RETURN @results
		END
		EXEC @hr = sp_OASetProperty @objRegExp, 'Pattern', @regexp
		IF @hr <> 0 BEGIN
			SET @results = 0
			RETURN @results
		END
		EXEC @hr = sp_OASetProperty @objRegExp, 'Global', false
		IF @hr <> 0 BEGIN
			SET @results = 0
			RETURN @results
		END
		EXEC @hr = sp_OASetProperty @objRegExp, 'IgnoreCase', @ignorecase
		IF @hr <> 0 BEGIN
			SET @results = 0
			RETURN @results
		END	
		EXEC @hr = sp_OAMethod @objRegExp, 'Test', @results OUTPUT, @source
		IF @hr <> 0 BEGIN
			SET @results = 0
			RETURN @results
		END
		EXEC @hr = sp_OADestroy @objRegExp
		IF @hr <> 0 BEGIN
			SET @results = 0
			RETURN @results
		END
	RETURN @results
	END
'''
