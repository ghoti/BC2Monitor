<html>
<body>
%if date:
Best of Stats for {{date}}<p>

%if kills:
{{date}} has {{kills}} kills<p>
%else:
There doesn't seem to be any kills this day :(<p>
%end
%if deaths:
        {{date}} has {{deaths}} deaths<p>
%else:
    There doesn't seem to be any kills this day :(<p>
%end
%if chat:
        {{date}} has {{chat}} chat lines<p>
%else:
    There doesn't seem to be any chat this day :(<p>
%end
%if ratio:
    {{date}} had a ratio of {{ratio}}<p>
%else:
    There doesn't seem to be any ratios this day:(<p>
%end
%else:
    Player not found :(<p>
%end
</body>
</html>