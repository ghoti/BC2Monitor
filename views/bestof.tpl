<html>
<body>
Best of Stats for {{date}}<p>
%if kills:
{{kills[0]}} has the most kills with {{kills[1]}} kills<p>
%else:
There doesn't seem to be any kills this day :(<p>
%end
%if deaths:
        {{deaths[0]}} has the most deaths with {{deaths[1]}} deaths<p>
%else:
    There doesn't seem to be any kills this day :(<p>
%end
%if chat:
        {{chat[0]}} was the most chattiest with {{chat[1]}} chat lines<p>
%else:
    There doesn't seem to be any kills this day :(<p>
%end
%if ratio:
    {{ratio[0]}} had the best ratio with a ratio of {{ratio[1]}}<p>
%else:
    There doesn't seem to be any ratios this day:(<p>
%end
</body>
</html>