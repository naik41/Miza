(this.webpackJsonpmizaweb2=this.webpackJsonpmizaweb2||[]).push([[38],{117:function(e,t){function n(e){return e?"string"===typeof e?e:e.source:null}function a(e){return r("(?:",e,")?")}function r(){for(var e=arguments.length,t=new Array(e),a=0;a<e;a++)t[a]=arguments[a];var r=t.map((function(e){return n(e)})).join("");return r}e.exports=function(e){var t,n=e.COMMENT("//","$",{contains:[{begin:/\\\n/}]}),i="decltype\\(auto\\)",s="[a-zA-Z_]\\w*::",c="(?!struct)(decltype\\(auto\\)|"+a(s)+"[a-zA-Z_]\\w*"+a("<[^<>]+>")+")",o={className:"type",begin:"\\b[a-z\\d_]*_t\\b"},l={className:"string",variants:[{begin:'(u8?|U|L)?"',end:'"',illegal:"\\n",contains:[e.BACKSLASH_ESCAPE]},{begin:"(u8?|U|L)?'(\\\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4,8}|[0-7]{3}|\\S)|.)",end:"'",illegal:"."},e.END_SAME_AS_BEGIN({begin:/(?:u8?|U|L)?R"([^()\\ ]{0,16})\(/,end:/\)([^()\\ ]{0,16})"/})]},u={className:"number",variants:[{begin:"\\b(0b[01']+)"},{begin:"(-?)\\b([\\d']+(\\.[\\d']*)?|\\.[\\d']+)((ll|LL|l|L)(u|U)?|(u|U)(ll|LL|l|L)?|f|F|b|B)"},{begin:"(-?)(\\b0[xX][a-fA-F0-9']+|(\\b[\\d']+(\\.[\\d']*)?|\\.[\\d']+)([eE][-+]?[\\d']+)?)"}],relevance:0},d={className:"meta",begin:/#\s*[a-z]+\b/,end:/$/,keywords:{keyword:"if else elif endif define undef warning error line pragma _Pragma ifdef ifndef include"},contains:[{begin:/\\\n/,relevance:0},e.inherit(l,{className:"string"}),{className:"string",begin:/<.*?>/},n,e.C_BLOCK_COMMENT_MODE]},p={className:"title",begin:a(s)+e.IDENT_RE,relevance:0},_=a(s)+e.IDENT_RE+"\\s*\\(",m={type:["bool","char","char16_t","char32_t","char8_t","double","float","int","long","short","void","wchar_t"],keyword:["alignas","alignof","and","and_eq","asm","atomic_cancel","atomic_commit","atomic_noexcept","auto","bitand","bitor","break","case","catch","class","co_await","co_return","co_yield","compl","concept","const","const_cast|10","consteval","constexpr","constinit","continue","decltype","default","delete","do","dynamic_cast|10","else","enum","explicit","export","extern","false","final","for","friend","goto","if","import","inline","module","mutable","namespace","new","noexcept","not","not_eq","nullptr","operator","or","or_eq","override","private","protected","public","reflexpr","register","reinterpret_cast|10","requires","return","signed","sizeof","static","static_assert","static_cast|10","struct","switch","synchronized","template","this","thread_local","throw","transaction_safe","transaction_safe_dynamic","true","try","typedef","typeid","typename","union","unsigned","using","virtual","volatile","while","xor","xor_eq,"],literal:["NULL","false","nullopt","nullptr","true"],built_in:["_Pragma"],_type_hints:["any","auto_ptr","barrier","binary_semaphore","bitset","complex","condition_variable","condition_variable_any","counting_semaphore","deque","false_type","future","imaginary","initializer_list","istringstream","jthread","latch","lock_guard","multimap","multiset","mutex","optional","ostringstream","packaged_task","pair","promise","priority_queue","queue","recursive_mutex","recursive_timed_mutex","scoped_lock","set","shared_future","shared_lock","shared_mutex","shared_timed_mutex","shared_ptr","stack","string_view","stringstream","timed_mutex","thread","true_type","tuple","unique_lock","unique_ptr","unordered_map","unordered_multimap","unordered_multiset","unordered_set","variant","vector","weak_ptr","wstring","wstring_view"]},f={className:"function.dispatch",relevance:0,keywords:{_hint:["abort","abs","acos","apply","as_const","asin","atan","atan2","calloc","ceil","cerr","cin","clog","cos","cosh","cout","declval","endl","exchange","exit","exp","fabs","floor","fmod","forward","fprintf","fputs","free","frexp","fscanf","future","invoke","isalnum","isalpha","iscntrl","isdigit","isgraph","islower","isprint","ispunct","isspace","isupper","isxdigit","labs","launder","ldexp","log","log10","make_pair","make_shared","make_shared_for_overwrite","make_tuple","make_unique","malloc","memchr","memcmp","memcpy","memset","modf","move","pow","printf","putchar","puts","realloc","scanf","sin","sinh","snprintf","sprintf","sqrt","sscanf","std","stderr","stdin","stdout","strcat","strchr","strcmp","strcpy","strcspn","strlen","strncat","strncmp","strncpy","strpbrk","strrchr","strspn","strstr","swap","tan","tanh","terminate","to_underlying","tolower","toupper","vfprintf","visit","vprintf","vsprintf"]},begin:r(/\b/,/(?!decltype)/,/(?!if)/,/(?!for)/,/(?!while)/,e.IDENT_RE,(t=/(<[^<>]+>|)\s*\(/,r("(?=",t,")")))},g=[f,d,o,n,e.C_BLOCK_COMMENT_MODE,u,l],b={variants:[{begin:/=/,end:/;/},{begin:/\(/,end:/\)/},{beginKeywords:"new throw return else",end:/;/}],keywords:m,contains:g.concat([{begin:/\(/,end:/\)/,keywords:m,contains:g.concat(["self"]),relevance:0}]),relevance:0},h={className:"function",begin:"("+c+"[\\*&\\s]+)+"+_,returnBegin:!0,end:/[{;=]/,excludeEnd:!0,keywords:m,illegal:/[^\w\s\*&:<>.]/,contains:[{begin:i,keywords:m,relevance:0},{begin:_,returnBegin:!0,contains:[p],relevance:0},{begin:/::/,relevance:0},{begin:/:/,endsWithParent:!0,contains:[l,u]},{relevance:0,match:/,/},{className:"params",begin:/\(/,end:/\)/,keywords:m,relevance:0,contains:[n,e.C_BLOCK_COMMENT_MODE,l,u,o,{begin:/\(/,end:/\)/,keywords:m,relevance:0,contains:["self",n,e.C_BLOCK_COMMENT_MODE,l,u,o]}]},o,n,e.C_BLOCK_COMMENT_MODE,d]};return{name:"C++",aliases:["cc","c++","h++","hpp","hh","hxx","cxx"],keywords:m,illegal:"</",classNameAliases:{"function.dispatch":"built_in"},contains:[].concat(b,h,f,g,[d,{begin:"\\b(deque|list|queue|priority_queue|pair|stack|vector|map|set|bitset|multiset|multimap|unordered_map|unordered_set|unordered_multiset|unordered_multimap|array|tuple|optional|variant|function)\\s*<",end:">",keywords:m,contains:["self",o]},{begin:e.IDENT_RE+"::",keywords:m},{match:[/\b(?:enum(?:\s+(?:class|struct))?|class|struct|union)/,/\s+/,/\w+/],className:{1:"keyword",3:"title.class"}}])}}}}]);
//# sourceMappingURL=38.be98c6fe.chunk.js.map