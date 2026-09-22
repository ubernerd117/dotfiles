return {
  {
    "ellisonleao/glow.nvim",
    config = true,
    cmd = "Glow",
    keys = {
      {
        "<leader>um",
        function()
          vim.cmd("Glow")
          if vim.bo.filetype == "glowpreview" and vim.api.nvim_win_get_config(0).relative ~= "" then
            local preview = vim.api.nvim_get_current_win()
            vim.cmd("tabnew")
            local placeholder = vim.api.nvim_get_current_win()
            vim.bo.bufhidden = "wipe"
            vim.api.nvim_win_set_config(preview, { relative = "", split = "right", win = placeholder })
            vim.api.nvim_set_current_win(preview)
            vim.api.nvim_win_close(placeholder, true)
          end
        end,
        desc = "Open Glow Markdown Preview in Tab",
      },
    },
  },
}
