$(document).ready(function() {

  $.getJSON("/orgchart/json", function(data) {

    var container = document.getElementById("chart-container");

    traverse(data);

    function render(parent, node) {
      var child = document.createElement("li");
      var link = document.createElement("a");
      var name = document.createTextNode(node.name);
      link.appendChild(name);
      child.appendChild(link);
      parent.appendChild(child);
      link.setAttribute("data-toggle", "collapse");
      link.setAttribute("data-parent", "#" + parent.id);
      return child;
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
        parent.setAttribute("id", count);
        parent.setAttribute("data-level", curr.level);
        parent.classList.add((parent.id === "1") ? "no.collapse" : "collapse");
        curr.dom_element.appendChild(parent);

        // Fix parent href to point to children
        curr.dom_element.querySelectorAll("a").forEach(function(elem) {
          elem.setAttribute("href", "#" + count);
        });
        count++;

        if (curr.children === undefined) {
          continue;
        }

        curr.children.forEach(function(elem) {
          if (!elem.visited) {
            // Render child node
            child = render(parent, elem);

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
