(this.webpackJsonpmizaweb2=this.webpackJsonpmizaweb2||[]).push([[303,115],{194:function(n,e){function i(n){return n?"string"===typeof n?n:n.source:null}function a(n){return s("(?=",n,")")}function s(){for(var n=arguments.length,e=new Array(n),a=0;a<n;a++)e[a]=arguments[a];var s=e.map((function(n){return i(n)})).join("");return s}n.exports=function(n){var e={className:"variable",variants:[{begin:/\$\d+/},{begin:/\$\{\w+\}/},{begin:s(/[$@]/,n.UNDERSCORE_IDENT_RE)}]},i={endsWithParent:!0,keywords:{$pattern:/[a-z_]{2,}|\/dev\/poll/,literal:["on","off","yes","no","true","false","none","blocked","debug","info","notice","warn","error","crit","select","break","last","permanent","redirect","kqueue","rtsig","epoll","poll","/dev/poll"]},relevance:0,illegal:"=>",contains:[n.HASH_COMMENT_MODE,{className:"string",contains:[n.BACKSLASH_ESCAPE,e],variants:[{begin:/"/,end:/"/},{begin:/'/,end:/'/}]},{begin:"([a-z]+):/",end:"\\s",endsWithParent:!0,excludeEnd:!0,contains:[e]},{className:"regexp",contains:[n.BACKSLASH_ESCAPE,e],variants:[{begin:"\\s\\^",end:"\\s|\\{|;",returnEnd:!0},{begin:"~\\*?\\s+",end:"\\s|\\{|;",returnEnd:!0},{begin:"\\*(\\.[a-z\\-]+)+"},{begin:"([a-z\\-]+\\.)+\\*"}]},{className:"number",begin:"\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}(:\\d{1,5})?\\b"},{className:"number",begin:"\\b\\d+[kKmMgGdshdwy]?\\b",relevance:0},e]};return{name:"Nginx config",aliases:["nginxconf"],contains:[n.HASH_COMMENT_MODE,{beginKeywords:"upstream location",end:/;|\{/,contains:i.contains,keywords:{section:"upstream location"}},{className:"section",begin:s(n.UNDERSCORE_IDENT_RE+a(/\s+\{/)),relevance:0},{begin:a(n.UNDERSCORE_IDENT_RE+"\\s"),end:";|\\{",contains:[{className:"attribute",begin:n.UNDERSCORE_IDENT_RE,starts:i}],relevance:0}],illegal:"[^\\s\\}\\{]"}}},689:function(n,e,i){!function n(){n.warned||(n.warned=!0,console.log('Deprecation (warning): Using file extension in specifier is deprecated, use "highlight.js/lib/languages/nginx" instead of "highlight.js/lib/languages/nginx.js"'))}(),n.exports=i(194)}}]);
//# sourceMappingURL=303.9ff8243f.chunk.js.map