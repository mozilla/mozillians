$(document).ready(function() {

  $.getJSON("/orgchart/json", function(data) {

    var container = document.getElementById("chart-container");

    traverse(data);


    function render(parent, node, count) {
      var child = document.createElement("li");
      var label = document.createElement("label");
      var link = document.createElement("a");
      var div = document.createElement("div");
      var name = document.createTextNode(node.name);

      link.setAttribute("href", node.href);



      div.classList.add("toggle");
      if (!node.children) {
        child.classList.add("leaf");
      } else {
        var input = document.createElement("input");
        input.setAttribute("id", count);
        input.type = "checkbox";
        parent.appendChild(input);
        label.setAttribute("for", count);
      }

      link.appendChild(name);
      label.appendChild(link);
      div.appendChild(label);
      child.appendChild(div);
      parent.appendChild(child);
      return div;
    };

    function traverse(root) {
      var queue = [root];
      var count = 0;

      // Mark node as visited
      root.visited = true;
      root.dom_element = container;
      root.level = 0;
      count++;

      while (queue.length > 0) {
        var curr = queue.shift();
        parent = document.createElement("ul");


        if (curr.children === undefined) {
          continue;
        }

        curr.dom_element.appendChild(parent);
        curr.children.forEach(function(elem) {
          if (!elem.visited) {
            // Render child node
            child = render(parent, elem, count);

            count++;
            // Mark child node as visited
            elem.visited = true;
            elem.dom_element = child;
            elem.level = curr.level + 1;
            queue.push(elem);
          };
        });
      };
    };
  });
});
