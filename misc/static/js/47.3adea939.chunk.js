(this.webpackJsonpmizaweb2=this.webpackJsonpmizaweb2||[]).push([[47],{126:function(n,e){function t(n){return n?"string"===typeof n?n:n.source:null}function a(n){var e=n[n.length-1];return"object"===typeof e&&e.constructor===Object?(n.splice(n.length-1,1),e):{}}function i(){for(var n=arguments.length,e=new Array(n),i=0;i<n;i++)e[i]=arguments[i];var c=a(e),r="("+(c.capture?"":"?:")+e.map((function(n){return t(n)})).join("|")+")";return r}n.exports=function(n){return{name:"Diff",aliases:["patch"],contains:[{className:"meta",relevance:10,match:i(/^@@ +-\d+,\d+ +\+\d+,\d+ +@@/,/^\*\*\* +\d+,\d+ +\*\*\*\*$/,/^--- +\d+,\d+ +----$/)},{className:"comment",variants:[{begin:i(/Index: /,/^index/,/={3,}/,/^-{3}/,/^\*{3} /,/^\+{3}/,/^diff --git/),end:/$/},{match:/^\*{15}$/}]},{className:"addition",begin:/^\+/,end:/$/},{className:"deletion",begin:/^-/,end:/$/},{className:"addition",begin:/^!/,end:/$/}]}}}}]);
//# sourceMappingURL=47.3adea939.chunk.js.map