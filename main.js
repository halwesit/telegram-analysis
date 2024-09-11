const fs = require("fs");

function extractNames(data) {
  return data
    .map((item) => {
      if (item.user) {
        return ["id:" + item.id, "name: " + item.user]
          .filter(Boolean)
          .join(" ");
      } else {
        return ["id:" + item.id, "name: " + item.first_name, item.last_name]
          .filter(Boolean)
          .join(" ");
      }
    })
    .filter(Boolean);
}

// Read JSON file
fs.readFile("user_data.json", "utf8", (err, jsonString) => {
  if (err) {
    console.log("Error reading file:", err);
    return;
  }
  try {
    const data = JSON.parse(jsonString);
    const result = extractNames(data);

    // Write results to a file
    fs.writeFile("results.txt", result.join("\n"), "utf8", (err) => {
      if (err) {
        console.log("Error writing file:", err);
      } else {
        console.log("Results have been written to results.txt");
      }
    });
  } catch (err) {
    console.log("Error parsing JSON string:", err);
  }
});
