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
